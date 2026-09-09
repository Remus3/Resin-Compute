"""The cross-check that keeps the non-128 SKIP in `tests/conftest.py` honest.

WHY THIS FILE EXISTS.

An adjudicated ruling kept the non-128 SKIP path in `tests/conftest.py`. Its
whole safety argument is one arm in another module:

    tests/test_commit_trailers.py
        ::test_the_missing_git_skip_path_is_not_taken_in_a_real_checkout

That arm reddens the suite if `git_unusable_reason()` ever returns a reason
inside a real checkout - which would evaporate every git-dependent guard under
`tests/` at once while the suite still reported green. Vacuous green is worse
than a missing test because it reads as coverage.

NOTHING PINNED THAT ARM. This module pins it, and pins BOTH of its branches.

THE FOUR HOLES THIS MODULE EXISTS TO CLOSE, each measured against the attempt it
replaces:

  1. DELETING THE CROSS-CHECK'S ENTIRE `else:` BLOCK left the previous attempt at
     2 passed. An arm that names the archive branch but cannot see it removed is
     not pinning it. Here the archive branch is FORCED by repointing the audited
     module's `REPO_ROOT` at a directory with no `.git` at or above it, and the
     arm asserts the AssertionError actually arrives.
  2. "WITH A TRUE REASON" WAS UNPINNED. Mutating the 128 branch to `return "x"`
     still passed, because the reason TEXT was never inspected and no arm ever
     asserted a SKIP is really raised. Here the failure message must CARRY the
     reason it was handed, and a separate arm drives the real classifier and
     asserts `Skipped` is raised with the 128 wording in it.
  3. A REAL SKIP DOOR, AND THE BINDING THAT DECIDES WHETHER IT OPENS. Inserting
     `require_git_repository()` into the cross-check turns the checkout arm into
     SKIPPED - a green-looking non-result - because `Skipped` derives from
     `BaseException` and ESCAPES `pytest.raises(AssertionError)`. Every
     expectation here goes through `_expect_assertion_error` or
     `_expect_no_raise`, which catch `BaseException` and reject `Skipped` by
     name.
     THAT DEFENCE WAS PRESENT AND UNREACHABLE, and this module's docstring
     asserted it was closed while it was not. Measured at e714b35: inserting
     `require_git_repository()` into the cross-check left this file at 12 passed,
     exit 0 - the mutant SURVIVED. Cause: every arm stubbed only
     `audited.git_unusable_reason`, the re-imported binding in
     `tests/test_commit_trailers.py`. `require_git_repository()` lives in
     `tests/conftest.py` and resolves `git_unusable_reason` in CONFTEST's
     globals, which answered None for this real checkout, so no `Skipped` was
     ever raised and the defence never fired. `_stub_reason()` now patches BOTH
     bindings - see its docstring for why each one is separately load-bearing -
     and `test_the_two_binding_stub_is_load_bearing_for_the_skip_door` pins the
     mechanism directly so dropping either patch reddens here immediately.
  4. A FOURTH DISPOSITION NOBODY HAD NAMED. With `GIT_DIR` exported,
     `git rev-parse --git-dir` SUCCEEDS while no `.git` sits on disk. The helper
     and the disk probe then DISAGREE: the checkout arm self-skips calling the
     population "archive-shaped" while git is FULLY USABLE - a FALSE reason - and
     the archive arm goes FALSE-RED. Neither arm of the previous attempt cleared
     `GIT_DIR` or `GIT_WORK_TREE`. An autouse fixture here deletes both from the
     environment so the environment cannot decide any verdict in this file.

WHICH BRANCH IS LIVE, AND THE CEILING ON THAT.

`(p / ".git").exists()` is TRUE for a `.git` FILE as well as a directory, so the
CHECKOUT branch is the live one in a linked worktree - where `.git` is a file -
and equally in the main checkout, where it is a directory. THE ARCHIVE BRANCH IS
UNREACHABLE FROM ANY CHECKOUT WITHOUT INTERVENTION. It is reached here only by
monkeypatching the audited module's `REPO_ROOT`, which is why that is done rather
than skipped: an arm that waits for a `git archive` extract to exist is an arm
that never runs.

WHAT THIS MODULE DOES NOT CLAIM. It does not run the cross-check inside a real
archive extract, and it does not verify that a real archive extract produces the
128 exit - `tests/test_conftest_git_gate.py` stubs that. It grades the arm's
LOGIC under forced inputs, not the world.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from _pytest.outcomes import Skipped

from tests import conftest
from tests import test_commit_trailers as audited

#: The cross-check under audit, resolved by name so a rename reddens here rather
#: than silently grading nothing.
CROSS_CHECK_NAME = "test_the_missing_git_skip_path_is_not_taken_in_a_real_checkout"

#: A reason distinctive enough that finding it inside the failure message proves
#: the message CARRIES the helper's answer rather than merely mentioning one.
SENTINEL_REASON = "SENTINEL-1a2b3c: git is unusable and this text must reach the failure"

#: The GENUINE `@lru_cache(maxsize=1)` wrapper, captured at import time - before
#: any arm can stub it. Cache clearing must go through this object rather than
#: through whatever is currently bound to `conftest.git_unusable_reason`: once
#: `_stub_reason()` has installed a plain lambda there, the name no longer has a
#: `cache_clear` attribute, and a teardown that reached for it by name would die
#: with AttributeError instead of clearing anything. Module import happens at
#: collection, before any test body runs, so this is the real one.
_REAL_GIT_UNUSABLE_REASON = conftest.git_unusable_reason

#: Hand-typed fragment of the exit-128 reason in `tests/conftest.py`. Typed here,
#: not read from that file: an arm that reads its own expected answer out of the
#: file it audits cannot see that answer be wrong.
EXPECTED_128_FRAGMENT = "this tree is not a git repository, so trackedness cannot be established"


@pytest.fixture(autouse=True)
def _neutralise_git_env_and_cache(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Delete `GIT_DIR`/`GIT_WORK_TREE` and clear the helper's cache both sides.

    `GIT_DIR` is the fourth disposition from this module's docstring: with it
    exported, git answers successfully for a tree that has no `.git` on disk, so
    the helper and the disk probe disagree and BOTH branches of the cross-check
    reach a wrong verdict. Deleting it here means no arm in this file can be
    decided by the ambient environment.

    `git_unusable_reason` is `@lru_cache(maxsize=1)`. Cleared BEFORE so no arm
    reads an answer cached by a real probe or an earlier arm, and AFTER so the
    rest of the suite never reads an answer cached from a stub - without the
    second clear a mutant survives vacuously.

    Both clears go through `_REAL_GIT_UNUSABLE_REASON`, not through the current
    value of `conftest.git_unusable_reason`. `monkeypatch` is set up BEFORE this
    fixture and therefore torn down AFTER it, so at the post-yield line a stub
    installed by `_stub_reason()` is STILL bound - and a lambda has no
    `cache_clear`. Reaching for it by name would raise AttributeError in
    teardown and leave the real cache uncleared for the rest of the suite.
    """
    monkeypatch.delenv("GIT_DIR", raising=False)
    monkeypatch.delenv("GIT_WORK_TREE", raising=False)
    _REAL_GIT_UNUSABLE_REASON.cache_clear()
    yield
    _REAL_GIT_UNUSABLE_REASON.cache_clear()


def _stub_reason(monkeypatch: pytest.MonkeyPatch, reason: str | None) -> None:
    """Make `git_unusable_reason()` answer `reason` at BOTH of its bindings.

    TWO PATCH TARGETS, EACH LOAD-BEARING FOR A DIFFERENT REASON, which is why
    this patches both rather than picking one:

      - `audited.git_unusable_reason` is the re-imported binding that the
        cross-check's OWN body calls. `tests/test_commit_trailers.py` does
        `from tests.conftest import git_unusable_reason` at import time, so the
        name is bound into that module's namespace. Without this patch the arms
        below grade the REAL tree instead of the forced input, and every
        expectation about a reason evaporates.
      - `conftest.git_unusable_reason` is the DEFINITION site, and it is what
        `require_git_repository()` and `skip_module_without_git()` resolve when
        they look the name up in their own module globals. Without this patch a
        `require_git_repository()` call inserted anywhere in the cross-check
        reads the real checkout's answer - None - raises no `Skipped`, and the
        skip-door defence in `_expect_assertion_error` never fires. That was the
        measured survivor at e714b35.

    Patching only one is a split brain: the cross-check's own arithmetic and the
    helpers it may call would disagree about whether git works, and an arm can
    then pass while grading a world that does not exist. Both bindings therefore
    get the SAME value, so the stubbed world is internally coherent.

    The real cache is cleared here too - `lru_cache` is on the object being
    shadowed, and an answer cached by an earlier arm would otherwise be handed
    to code that bypasses the stub.
    """
    _REAL_GIT_UNUSABLE_REASON.cache_clear()
    monkeypatch.setattr(conftest, "git_unusable_reason", lambda: reason)
    monkeypatch.setattr(audited, "git_unusable_reason", lambda: reason)


def _cross_check() -> Callable[[], None]:
    """The audited arm itself, or a failure naming the rename that broke this."""
    fn = getattr(audited, CROSS_CHECK_NAME, None)
    assert callable(fn), (
        f"tests/test_commit_trailers.py no longer defines {CROSS_CHECK_NAME}. The non-128 "
        "SKIP in tests/conftest.py rests entirely on that arm, so its disappearance is "
        "the defect, not this test's problem"
    )
    return fn


def _expect_assertion_error(fn: Callable[[], None], fragment: str) -> str:
    """Assert `fn()` raises an AssertionError whose message contains `fragment`.

    Catches `BaseException`, not `Exception`, and rejects `Skipped` explicitly.
    `Skipped` derives from `BaseException`, so `pytest.raises(AssertionError)` -
    and even `pytest.raises(Exception)` - lets it through, and a skip escaping
    here reads as a green non-result. That door was a measured survivor.
    """
    try:
        fn()
    except Skipped as skipped:
        raise AssertionError(
            f"the cross-check SKIPPED instead of failing: {skipped!r}. A skip is a "
            "green-looking non-result - it escapes pytest.raises(AssertionError) because "
            "Skipped derives from BaseException - so the arm that guards every "
            "git-dependent guard under tests/ would silently stop guarding"
        ) from skipped
    except AssertionError as failure:
        message = str(failure)
        assert fragment in message, (
            f"the cross-check failed, but not for the reason under test. Expected the "
            f"message to contain {fragment!r}; got {message!r}"
        )
        return message
    except BaseException as other:  # pragma: no cover - defensive
        raise AssertionError(
            f"the cross-check raised {type(other).__name__} rather than AssertionError: {other!r}"
        ) from other
    raise AssertionError(
        "the cross-check PASSED where it must fail. That is the vacuous-green shape this "
        "whole module exists to detect"
    )


def _expect_no_raise(fn: Callable[[], None], what: str) -> None:
    """Assert `fn()` completes - the arm must not be a false red on a good tree."""
    try:
        fn()
    except Skipped as skipped:  # pragma: no cover
        raise AssertionError(f"{what}: the cross-check skipped rather than passing: {skipped!r}") from skipped
    except BaseException as failure:
        raise AssertionError(
            f"{what}: the cross-check raised {type(failure).__name__} on a shape it must "
            f"accept - that is a false red: {failure!r}"
        ) from failure


def _force_checkout_shape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Repoint the audited module's REPO_ROOT at a directory that HAS a `.git`.

    Written as a FILE, the shape a linked worktree really has, because
    `Path.exists()` is true for both and the cross-check deliberately does not
    care which.
    """
    root = tmp_path / "checkout_shape"
    root.mkdir()
    (root / ".git").write_bytes(b"gitdir: ../elsewhere/.git/worktrees/x\n")
    monkeypatch.setattr(audited, "REPO_ROOT", root)
    assert (root / ".git").exists(), "precondition: the forced checkout shape must have a .git entry"
    return root


def _force_archive_shape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Repoint REPO_ROOT at a directory with NO `.git` at or above it.

    The absence is ASSERTED, not assumed. If a `.git` existed anywhere up the
    temporary path the cross-check would take its checkout branch and the arm
    would be grading the other half - passing while measuring nothing.
    """
    root = tmp_path / "archive_shape"
    root.mkdir()
    monkeypatch.setattr(audited, "REPO_ROOT", root)
    found = [p for p in (root, *root.parents) if (p / ".git").exists()]
    assert not found, (
        f"precondition failed: a .git entry exists at {found[0] if found else None}, at or above "
        f"{root}, so the archive branch of the cross-check is not reachable from here and this "
        "arm would grade the checkout branch instead"
    )
    return root


# ---------------------------------------------------------------------------
# The checkout branch: a reason inside a real checkout MUST redden.
# ---------------------------------------------------------------------------


def test_a_reason_inside_a_checkout_reddens_and_the_message_carries_that_reason(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """This is the proposition the kept SKIP path depends on, asserted directly.

    Not merely "it fails" - the failure message must CONTAIN the reason it was
    handed. A message that only said "git is unusable" would pass a non-None
    check while telling the reader nothing, and the reason TEXT going uninspected
    was a measured survivor.
    """
    root = _force_checkout_shape(monkeypatch, tmp_path)
    _stub_reason(monkeypatch, SENTINEL_REASON)
    message = _expect_assertion_error(_cross_check(), SENTINEL_REASON)
    assert str(root) in message, (
        f"the failure must name WHERE the .git entry was found so the reader can act on it; "
        f"{str(root)!r} is absent from {message!r}"
    )


@pytest.mark.parametrize("reason", ["x", "", " ", "0", "git is fine actually"])
def test_any_non_none_reason_inside_a_checkout_reddens_even_a_falsy_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, reason: str
) -> None:
    """A truthiness check is not the contract - `is not None` is.

    An empty or whitespace reason is still a reason: `require_git_repository()`
    skips on `reason is not None`, so an empty string disarms every guard just as
    thoroughly as a sentence does, while reading as harmless. The cross-check
    must redden for all of them.
    """
    _force_checkout_shape(monkeypatch, tmp_path)
    _stub_reason(monkeypatch, reason)
    _expect_assertion_error(_cross_check(), "so this IS a checkout")


def test_no_reason_inside_a_checkout_is_a_pass_and_not_a_false_red(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The control for the arm above: a healthy checkout must NOT redden.

    Without this, an arm welded to "always fail" would satisfy every expectation
    in this module while destroying the suite.
    """
    _force_checkout_shape(monkeypatch, tmp_path)
    _stub_reason(monkeypatch, None)
    _expect_no_raise(_cross_check(), "a checkout whose git answers cleanly")


# ---------------------------------------------------------------------------
# The archive branch: the half nothing previously pinned.
# ---------------------------------------------------------------------------


def test_a_usable_git_with_no_disk_dot_git_reddens_the_archive_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Deleting the cross-check's `else:` block must be VISIBLE, and here it is.

    Measured against the attempt this file replaces: removing that whole block
    left it at 2 passed. This arm forces the archive shape and asserts the
    AssertionError arrives, so the deletion reddens.
    """
    _force_archive_shape(monkeypatch, tmp_path)
    _stub_reason(monkeypatch, None)
    _expect_assertion_error(_cross_check(), "the detector is not detecting")


def test_a_reason_with_no_disk_dot_git_is_a_pass_and_not_a_false_red(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The archive branch's control: an honest archive extract must NOT redden.

    That is the shape the whole SKIP mechanism exists to serve, so reddening here
    would be the false red that trains a reader to ignore red.
    """
    _force_archive_shape(monkeypatch, tmp_path)
    _stub_reason(monkeypatch, SENTINEL_REASON)
    _expect_no_raise(_cross_check(), "an archive extract with an honest reason")


# ---------------------------------------------------------------------------
# The reason TEXT, and that a SKIP is really raised.
# ---------------------------------------------------------------------------


def test_the_128_reason_text_actually_reaches_a_raised_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """A SKIP is really raised, and it carries the exit-128 wording.

    The previous attempt asserted neither. Mutating the 128 branch to
    `return "x"` survived it, because nothing inspected the text and nothing
    checked that `Skipped` was raised at all. `EXPECTED_128_FRAGMENT` is typed by
    hand in this file rather than imported from `tests/conftest.py`.
    """

    class _Fake:
        returncode = 128
        stdout = ""
        stderr = "fatal: not a git repository (or any of the parent directories): .git"

    class _FakeSubprocess:
        def run(self, argv: list[str], **kwargs: Any) -> _Fake:
            return _Fake()

    monkeypatch.setattr(conftest, "subprocess", _FakeSubprocess())
    _REAL_GIT_UNUSABLE_REASON.cache_clear()

    with pytest.raises(Skipped) as caught:
        conftest.require_git_repository()

    text = str(caught.value.msg)
    assert EXPECTED_128_FRAGMENT in text, (
        f"the exit-128 skip reason no longer contains the hand-typed fragment "
        f"{EXPECTED_128_FRAGMENT!r}. Got: {text!r}"
    )
    assert "128" in text, "the skip must quote git's own exit code so a reader can act on it"


def test_a_none_reason_raises_nothing_at_all_from_require_git_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-vacuity for the arm above: a usable git must not raise Skipped.

    A `require_git_repository()` welded to always skipping would satisfy the
    exit-128 arm and silently disarm the whole directory.
    """

    class _Fake:
        returncode = 0
        stdout = ".git\n"
        stderr = ""

    class _FakeSubprocess:
        def run(self, argv: list[str], **kwargs: Any) -> _Fake:
            return _Fake()

    monkeypatch.setattr(conftest, "subprocess", _FakeSubprocess())
    _REAL_GIT_UNUSABLE_REASON.cache_clear()
    conftest.require_git_repository()


# ---------------------------------------------------------------------------
# Which branch is live HERE, recorded rather than assumed.
# ---------------------------------------------------------------------------


def test_this_copy_takes_the_checkout_branch_and_says_which_dot_git_shape_it_has() -> None:
    """Records the live branch for THIS tree, so a reader is not left guessing.

    A linked worktree has a `.git` FILE and the main checkout has a DIRECTORY;
    `Path.exists()` is true for both, so both take the CHECKOUT branch and the
    archive branch is dead in either.

    IT SKIPS RATHER THAN FAILING WHEN NO `.git` IS ON DISK, and the first version
    of this arm got that wrong. An extract has nothing to report, which is
    NOT-PRESENT-AT-ALL - the third disposition - and asserting there turns the
    Download-ZIP population red for a fact about this machine. Measured
    2026-09-09 against a `git archive` extract outside any repository: the
    asserting version gave `1 failed, 13 passed`, a FALSE RED in the exact
    population this module reasons about. The skip below names that shape, and
    the arms above remain the only thing grading the archive half.
    """
    on_disk = [p for p in (audited.REPO_ROOT, *audited.REPO_ROOT.parents) if (p / ".git").exists()]
    if not on_disk:
        pytest.skip(
            "no .git entry at or above the audited module's REPO_ROOT, so this copy takes "
            "the ARCHIVE branch of the cross-check and there is no on-disk shape to record: "
            "that is the normal state of a Download-ZIP, sdist or `git archive` copy and it "
            "is SKIPPED rather than failed"
        )
    entry = on_disk[0] / ".git"
    assert entry.is_file() or entry.is_dir(), f"{entry} is neither a file nor a directory"


# ---------------------------------------------------------------------------
# The stub mechanism itself, pinned - hole 3's real closure.
# ---------------------------------------------------------------------------


def test_the_two_binding_stub_is_load_bearing_for_the_skip_door(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`_stub_reason()` must actually arm `require_git_repository()` to skip.

    This is the arm whose absence let the false green stand. The skip-door
    defence in `_expect_assertion_error` can only fire if a
    `require_git_repository()` call reached from the cross-check really raises
    `Skipped` under a stub - and that depends entirely on the DEFINITION-site
    patch, because the helper resolves `git_unusable_reason` in
    `tests/conftest.py`'s globals and never in the audited module's.

    Dropping the `conftest` patch from `_stub_reason()` reddens HERE, with a
    message naming the cause, rather than silently reopening hole 3 and leaving
    this module reporting 13 passed while grading nothing.

    The paired non-vacuity arm is
    `test_a_none_reason_stub_leaves_require_git_repository_silent`: without it a
    `require_git_repository()` welded to always skipping would satisfy this one.
    """
    _stub_reason(monkeypatch, SENTINEL_REASON)

    assert conftest.git_unusable_reason() == SENTINEL_REASON, (
        "the definition-site binding is not stubbed, so require_git_repository() will read "
        "the real checkout's answer and the skip door in _expect_assertion_error is dead code"
    )
    assert audited.git_unusable_reason() == SENTINEL_REASON, (
        "the audited module's re-imported binding is not stubbed, so the cross-check's own "
        "body would grade the real tree instead of the forced input"
    )

    with pytest.raises(Skipped) as caught:
        conftest.require_git_repository()

    assert SENTINEL_REASON in str(caught.value.msg), (
        f"require_git_repository() skipped, but not with the stubbed reason: "
        f"{caught.value.msg!r}"
    )


def test_a_none_reason_stub_leaves_require_git_repository_silent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-vacuity for the arm above: a None stub must raise NOTHING.

    Proves the arm above detects a real difference rather than passing because
    `require_git_repository()` skips unconditionally.
    """
    _stub_reason(monkeypatch, None)

    assert conftest.git_unusable_reason() is None
    conftest.require_git_repository()
