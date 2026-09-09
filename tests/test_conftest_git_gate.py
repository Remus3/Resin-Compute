"""Characterization of `tests/conftest.py`'s git-probe classifier.

WHY THIS FILE EXISTS.

`tests/conftest.py::git_unusable_reason()` runs `git rev-parse --git-dir` and
routes FOUR outcomes to three different skip reasons plus a usable verdict:

  - OSError from the exec itself -> "git is not runnable on this machine"
  - exit 128                     -> "this tree is not a git repository"
  - any OTHER non-zero exit      -> "git is present but did not answer"
  - exit 0                       -> None, git can answer

Measured 2026-09-08 before this file existed: NOTHING under `tests/` stubbed
`git rev-parse --git-dir`, so all three skip branches were separated by no test
at all. `grep -rn rev-parse tests/` found only the real invocation in
`tests/conftest.py`, prose about it, and three stubs in
`tests/test_hook_gate.py` that stub a DIFFERENT harness's git rather than this
helper's. The consequence, recorded in `tests/test_hook_interpreter.py` around
line 137: injecting exit 7 there gave 29 passed, 4 SKIPPED, exit 0 - four arms
evaporating green - and no arm anywhere noticed that the third branch had been
taken rather than the second.

WHAT THIS FILE DOES AND DOES NOT CLAIM.

It PINS today's behaviour, including the reason text each branch emits and the
fact that the three reasons are mutually DISTINGUISHABLE. A reader sent to
"install git", "clone the repository" and "your git is broken" needs three
different next steps, so collapsing any two of these into one string is a real
regression and is what these arms exist to catch.

It does NOT bless the DISPOSITION. Whether a git that is present and exits
non-zero for an unknown reason should SKIP - as it does today - or FAIL is an
open question, deliberately left open here and stated in the ceiling arm at the
bottom of this file.

HOW THE STUB WORKS, AND THE THREE TRAPS IN BUILDING IT.

  1. `git_unusable_reason` is `@lru_cache(maxsize=1)`. Every arm here clears the
     cache BEFORE and AFTER through an autouse fixture. Without both sides an
     arm pins whatever an earlier arm cached and its mutant survives vacuously.

  2. The stub replaces the `subprocess` NAME IN THE CONFTEST MODULE NAMESPACE.
     A PATH shim would measure the wrong thing on Windows: `shutil.which` is
     PATHEXT-aware but `subprocess.run` goes through CreateProcess, which
     appends only `.exe`, so a `git.bat` shim is visible to one and invisible to
     the other.

  3. `pytest.raises(Exception)` DOES NOT CATCH a skip. `Skipped` derives from
     `BaseException`, not `Exception`, and getting it wrong turns a guard
     green-by-skip. That fact is asserted directly rather than assumed.

The stub also ASSERTS IT WAS CALLED WITH THE REAL ARGV and cwd. A stub that
ignores its arguments cannot notice the probe command being changed underneath
it.
"""
from __future__ import annotations

from typing import Any

import pytest
from _pytest.outcomes import Failed, Skipped

from tests import conftest

#: The exact probe `tests/conftest.py` must issue. Pinned here so a silent
#: change of question - `--show-toplevel`, `status`, a different cwd - reddens
#: rather than being absorbed by a stub that answers anything.
EXPECTED_ARGV = ["git", "rev-parse", "--git-dir"]

#: Realistic stderr for the exit-128 case, as git itself prints it.
GIT_128_STDERR = "fatal: not a git repository (or any of the parent directories): .git"


class _FakeCompleted:
    """The three attributes of `CompletedProcess` this helper reads."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _RecordingSubprocess:
    """Stand-in for the `subprocess` MODULE as `tests/conftest.py` sees it.

    Records every call so an arm can assert the probe's argv and cwd, and either
    returns a canned `_FakeCompleted` or raises a canned exception.
    """

    def __init__(self, outcome: _FakeCompleted | BaseException) -> None:
        self._outcome = outcome
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def run(self, argv: list[str], **kwargs: Any) -> _FakeCompleted:
        self.calls.append((list(argv), dict(kwargs)))
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome


@pytest.fixture(autouse=True)
def _clear_git_reason_cache() -> Any:
    """Clear the lru_cache on BOTH sides of every arm in this module.

    Before, so an arm never reads an answer cached by a real probe or an earlier
    arm. After, so the rest of the suite - every module here imports this
    conftest - never reads an answer cached from a STUB.
    """
    conftest.git_unusable_reason.cache_clear()
    yield
    conftest.git_unusable_reason.cache_clear()


def _stub_git(monkeypatch: pytest.MonkeyPatch, outcome: _FakeCompleted | BaseException) -> _RecordingSubprocess:
    fake = _RecordingSubprocess(outcome)
    monkeypatch.setattr(conftest, "subprocess", fake)
    return fake


def _assert_probed_git_exactly_once(fake: _RecordingSubprocess) -> None:
    assert len(fake.calls) == 1, f"expected exactly one git probe, recorded {len(fake.calls)}: {fake.calls}"
    argv, kwargs = fake.calls[0]
    assert argv == EXPECTED_ARGV, f"the probe argv changed: expected {EXPECTED_ARGV}, got {argv}"
    assert kwargs.get("cwd") == conftest.REPO_ROOT, (
        f"the probe must run in {conftest.REPO_ROOT}, not {kwargs.get('cwd')!r} - a probe in the "
        "wrong directory answers a different question and `rev-parse --git-dir` WALKS UP"
    )
    assert kwargs.get("check") is False, "the probe must not raise on a non-zero exit - the exit code IS the signal"
    assert kwargs.get("capture_output") is True, "the reason text quotes git's own output, so it must be captured"
    assert kwargs.get("text") is True, "the reason text concatenates git's output as str, not bytes"


# ---------------------------------------------------------------------------
# The four outcomes of the probe.
# ---------------------------------------------------------------------------


def test_an_exec_failure_names_non_runnability_and_never_claims_a_missing_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OSError from the exec -> "git is not runnable on this machine".

    DISTINGUISHABILITY IS THE POINT. This branch must not borrow the
    not-a-repository wording: "install git" and "clone the repository" are
    different next steps, and a reader given the wrong one looks in the wrong
    place. The exception TYPE and MESSAGE must both survive into the reason,
    because FileNotFoundError and PermissionError on the same exec mean
    different things.
    """
    fake = _stub_git(monkeypatch, FileNotFoundError(2, "The system cannot find the file specified"))

    reason = conftest.git_unusable_reason()

    _assert_probed_git_exactly_once(fake)
    assert reason is not None, "an exec failure must not read as a usable git"
    assert "git is not runnable on this machine" in reason
    assert "FileNotFoundError" in reason, "the exception type is the actionable part and must survive"
    assert "The system cannot find the file specified" in reason
    assert "not a git repository" not in reason, (
        "a machine without git is NOT the same state as a directory without a repository, and this "
        f"reason conflates them: {reason}"
    )
    assert str(conftest.REPO_ROOT) in reason, "the reason must name the tree it could not establish trackedness for"


def test_exit_128_names_a_missing_repository_and_carries_gits_own_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exit 128 -> "this tree is not a git repository", quoting git's stderr.

    128 is git's own code for "not a repository", and this is the normal state
    of a Download-ZIP, sdist or `git archive` copy. The reason must say so AND
    carry git's own detail text, so a reader who hit some OTHER 128 can see
    which one they hit.
    """
    fake = _stub_git(monkeypatch, _FakeCompleted(128, stderr=GIT_128_STDERR))

    reason = conftest.git_unusable_reason()

    _assert_probed_git_exactly_once(fake)
    assert reason is not None
    assert "this tree is not a git repository" in reason
    assert "exited 128" in reason, "the exit code is the evidence and must be quoted verbatim"
    assert GIT_128_STDERR in reason, "git's own detail text must survive into the reason, not be summarised away"
    assert "not runnable" not in reason, "git ran fine here - claiming otherwise sends the reader to install git"


def test_a_non_128_non_zero_exit_names_that_code_and_is_a_distinct_reason_from_128(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exit 7 -> "git is present but did not answer", naming 7 verbatim.

    THIS IS THE ARM THAT HAD NEVER EXISTED. Before this file, exit 7 and exit
    128 both produced a skip and nothing anywhere distinguished them, so the
    branch at `tests/conftest.py:109` could have been deleted into the 128
    branch with the whole suite still green.
    """
    seven = _stub_git(monkeypatch, _FakeCompleted(7, stderr="error: something went sideways"))
    reason_seven = conftest.git_unusable_reason()
    _assert_probed_git_exactly_once(seven)

    assert reason_seven is not None, "a broken git must not read as a usable git"
    assert "git is present but did not answer" in reason_seven
    assert "exited 7" in reason_seven, (
        "the exit code must appear VERBATIM - a reason that says only 'non-zero' cannot tell a reader "
        f"which failure they hit: {reason_seven}"
    )
    assert "error: something went sideways" in reason_seven, "git's own detail text must survive"
    assert "not a git repository" not in reason_seven, (
        "exit 7 is a TOOL FAILURE, not an absent repository, and telling the reader to clone sends them "
        f"to fix something that is not broken: {reason_seven}"
    )

    conftest.git_unusable_reason.cache_clear()
    one_two_eight = _stub_git(monkeypatch, _FakeCompleted(128, stderr="error: something went sideways"))
    reason_128 = conftest.git_unusable_reason()
    _assert_probed_git_exactly_once(one_two_eight)

    assert reason_seven != reason_128, (
        "exit 7 and exit 128 must not produce the SAME reason string - they are different states with "
        "different next steps, and identical text is how the 7 branch becomes untestable"
    )


def test_exit_zero_reports_no_reason_at_all(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exit 0 -> None. The positive control for every arm above.

    Without this arm a classifier welded to "unusable" would pass all three
    negative arms, and every git-dependent guard under `tests/` would skip
    forever while the suite reported green.
    """
    fake = _stub_git(monkeypatch, _FakeCompleted(0, stdout=".git\n"))

    reason = conftest.git_unusable_reason()

    _assert_probed_git_exactly_once(fake)
    assert reason is None, f"exit 0 means git answered, so there is no reason to skip, but got: {reason}"


def test_the_detail_text_falls_back_from_stderr_to_stdout_to_a_named_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stderr, else stdout, else the literal "no output".

    Pinned because the fallback is what stops a silent git from producing a
    reason with an empty parenthesis, which reads as a truncated message rather
    than as "git said nothing".
    """
    fake = _stub_git(monkeypatch, _FakeCompleted(9, stdout="on stdout", stderr="on stderr"))
    assert "on stderr" in (conftest.git_unusable_reason() or "")
    assert "on stdout" not in (conftest.git_unusable_reason() or "")
    _assert_probed_git_exactly_once(fake)

    conftest.git_unusable_reason.cache_clear()
    _stub_git(monkeypatch, _FakeCompleted(9, stdout="on stdout", stderr="   "))
    assert "on stdout" in (conftest.git_unusable_reason() or ""), "a blank stderr must fall through to stdout"

    conftest.git_unusable_reason.cache_clear()
    _stub_git(monkeypatch, _FakeCompleted(9, stdout="", stderr=""))
    assert "no output" in (conftest.git_unusable_reason() or ""), (
        "with neither stream populated the reason must SAY git printed nothing, not render an empty detail"
    )


# ---------------------------------------------------------------------------
# The pure classifier, exercised with no subprocess at all.
# ---------------------------------------------------------------------------


def test_the_pure_classifier_gives_the_four_outcomes_four_distinct_categories() -> None:
    """`classify_git_probe` separates the outcomes STRUCTURALLY, not by prose.

    A category token is checkable without matching English, so a future reword
    of a reason string does not silently merge two branches. The four tokens
    must be pairwise distinct - that is the property the missing exit-7 arm was
    unable to state.
    """
    not_runnable = conftest.classify_git_probe(None, "", "", "FileNotFoundError: no git")
    missing_repo = conftest.classify_git_probe(128, "", GIT_128_STDERR, None)
    did_not_answer = conftest.classify_git_probe(7, "", "boom", None)
    usable = conftest.classify_git_probe(0, ".git\n", "", None)

    categories = [not_runnable[0], missing_repo[0], did_not_answer[0], usable[0]]
    assert len(set(categories)) == 4, f"the four outcomes must be pairwise distinct categories, got {categories}"
    assert not_runnable[0] == conftest.GIT_PROBE_NOT_RUNNABLE
    assert missing_repo[0] == conftest.GIT_PROBE_NOT_A_REPOSITORY
    assert did_not_answer[0] == conftest.GIT_PROBE_DID_NOT_ANSWER
    assert usable[0] == conftest.GIT_PROBE_USABLE

    assert usable[1] is None, "the usable category carries no skip reason"
    for category, reason in (not_runnable, missing_repo, did_not_answer):
        assert reason is not None and reason.strip(), f"{category} must carry a non-empty reason"

    reasons = [not_runnable[1], missing_repo[1], did_not_answer[1]]
    assert len(set(reasons)) == 3, f"the three unusable reasons must be pairwise distinct strings, got {reasons}"


def test_the_classifier_and_the_cached_helper_agree_on_every_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    """The refactor is behaviour-preserving: same input, byte-identical reason.

    Cross-checks the pure classifier against `git_unusable_reason()` driven
    through the stub. If the two ever drift, the classifier is documenting a
    branch the real helper no longer takes - which is worse than no arm, since
    it reads as coverage.
    """
    cases: list[tuple[_FakeCompleted | BaseException, tuple[int | None, str, str, str | None]]] = [
        (_FakeCompleted(0, stdout=".git\n"), (0, ".git\n", "", None)),
        (_FakeCompleted(128, stderr=GIT_128_STDERR), (128, "", GIT_128_STDERR, None)),
        (_FakeCompleted(7, stderr="boom"), (7, "", "boom", None)),
        (OSError("no exec for you"), (None, "", "", "OSError: no exec for you")),
    ]
    for outcome, pure_args in cases:
        conftest.git_unusable_reason.cache_clear()
        _stub_git(monkeypatch, outcome)
        through_helper = conftest.git_unusable_reason()
        _, through_classifier = conftest.classify_git_probe(*pure_args)
        assert through_helper == through_classifier, (
            f"the helper and the classifier disagree for {pure_args!r}:\n  helper:     {through_helper!r}\n"
            f"  classifier: {through_classifier!r}"
        )


def test_git_unusable_reason_still_returns_str_or_none_and_not_the_category_tuple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public signature is a merge surface and did not change.

    `tests/test_commit_trailers.py`, `tests/test_hook_gate.py` and
    `tests/test_line_endings.py` all consume this return value directly. A tuple
    leaking out here would break them, and a truthiness check on a tuple whose
    second element is None would break them SILENTLY.
    """
    _stub_git(monkeypatch, _FakeCompleted(0, stdout=".git\n"))
    assert conftest.git_unusable_reason() is None

    conftest.git_unusable_reason.cache_clear()
    _stub_git(monkeypatch, _FakeCompleted(7, stderr="boom"))
    unusable = conftest.git_unusable_reason()
    assert isinstance(unusable, str), f"the helper must return `str | None`, got {type(unusable).__name__}"


# ---------------------------------------------------------------------------
# The two skip helpers, both arms of each.
# ---------------------------------------------------------------------------


def test_require_git_repository_raises_skipped_when_a_reason_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """A run-time guard: reason present -> `Skipped`, carrying that reason."""
    _stub_git(monkeypatch, _FakeCompleted(128, stderr=GIT_128_STDERR))

    with pytest.raises(Skipped) as caught:
        conftest.require_git_repository()

    assert "this tree is not a git repository" in str(caught.value.msg)
    assert caught.value.allow_module_level is False, (
        "the run-time helper must skip the CURRENT test only - a module-level skip here would throw away "
        "every other test in the calling module, including ones that never touch git"
    )


def test_require_git_repository_is_a_no_op_when_git_can_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """The non-vacuity arm: usable git -> the guard must not skip anything.

    Without this, a helper hardwired to skip would satisfy the arm above and
    every git-dependent guard in this directory would evaporate while the suite
    still reported green.

    The `Skipped` is CAUGHT and converted to a failure rather than allowed to
    propagate. Letting it propagate makes this arm report as a SKIP under the
    very mutant it exists to kill, and a skip is not a failure - measured
    2026-09-08 against an inverted guard, where this arm went green-by-skip.
    """
    _stub_git(monkeypatch, _FakeCompleted(0, stdout=".git\n"))

    try:
        conftest.require_git_repository()
    except Skipped as skipped:
        pytest.fail(f"git answered exit 0, yet the run-time guard skipped: {skipped.msg}")


def test_skip_module_without_git_raises_skipped_at_module_level(monkeypatch: pytest.MonkeyPatch) -> None:
    """An import-time guard: reason present -> `Skipped` with allow_module_level.

    `allow_module_level=True` is the load-bearing flag. Without it pytest turns
    an import-time skip into a COLLECTION ERROR, which aborts the whole run
    rather than skipping one module - the exact failure `tests/conftest.py` was
    written to remove.
    """
    _stub_git(monkeypatch, _FakeCompleted(128, stderr=GIT_128_STDERR))

    with pytest.raises(Skipped) as caught:
        conftest.skip_module_without_git()

    assert caught.value.allow_module_level is True, (
        "without allow_module_level=True an import-time skip is reported as a collection ERROR and the "
        "entire suite aborts at exit 2"
    )
    assert "this tree is not a git repository" in str(caught.value.msg)


def test_skip_module_without_git_is_a_no_op_when_git_can_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """The non-vacuity arm for the import-time guard.

    Same reason for catching rather than propagating: an uncaught module-level
    `Skipped` here would report as a skip under the mutant this arm exists to
    kill, which is the failure mode being guarded against, not evidence.
    """
    _stub_git(monkeypatch, _FakeCompleted(0, stdout=".git\n"))

    try:
        conftest.skip_module_without_git()
    except Skipped as skipped:
        pytest.fail(f"git answered exit 0, yet the import-time guard skipped the module: {skipped.msg}")


def test_skipped_is_not_an_exception_subclass_so_a_broad_raises_would_not_catch_it() -> None:
    """The trap that has bitten three files in this tree, asserted as a fact.

    `pytest.raises(Exception)` around a call that skips does NOT catch the skip
    - `Skipped` derives from `BaseException` - so such a guard reports as
    green-by-skip rather than as a failure. Pinned here so the two arms above,
    which name `Skipped` explicitly, cannot be "simplified" into the broken form.
    """
    assert issubclass(Skipped, BaseException)
    assert not issubclass(Skipped, Exception), (
        "if this ever becomes true the raises(Exception) form stops being a trap, and this file's "
        "explicit-Skipped arms can be relaxed - until then they cannot"
    )


# ---------------------------------------------------------------------------
# The ceiling.
# ---------------------------------------------------------------------------


def test_a_present_but_broken_git_skips_today_and_whether_that_is_right_is_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """STATES THE CEILING. Today exit 7 SKIPS. This arm does not bless that.

    Whether a git that is installed, runnable, and exits non-zero for a reason
    nobody has classified should SKIP or FAIL is an OPEN QUESTION. This arm
    records only that today it produces a skip and not a failure, so that a
    future change of disposition is a DELIBERATE edit to this arm rather than an
    accident nothing noticed.

    The case for FAIL: there are three dispositions, not two - ran-and-found-
    nothing (skip), ran-and-BROKE (fail), and not-present-at-all (skip). Exit 7
    is the middle one, and routing it to a skip lets a broken tool read as an
    absent one.

    The case for SKIP, which is why this is not simply a defect: trackedness
    genuinely IS unknowable when git will not answer, the reason text is a
    DECLARED could-not-check that quotes the exit code rather than a disguised
    pass, and converting it to a failure risks installing a FALSE RED on a box
    where git is merely unusual - which is how a correct fix becomes a worse
    one.

    THIS ARM TAKES NO SIDE. An adjudicator rules on the disposition; this file
    only makes the branch visible.
    """
    _stub_git(monkeypatch, _FakeCompleted(7, stderr="error: something went sideways"))

    with pytest.raises(Skipped) as caught:
        conftest.require_git_repository()

    assert "exited 7" in str(caught.value.msg), "whatever the disposition, the reason must name the exit code"

    conftest.git_unusable_reason.cache_clear()
    _stub_git(monkeypatch, _FakeCompleted(7, stderr="error: something went sideways"))
    with pytest.raises(BaseException) as anything:  # noqa: B017
        conftest.require_git_repository()
    assert not isinstance(anything.value, Failed), (
        "today a broken git does not FAIL - if this arm reddens because it now does, that is the open "
        "question being answered, and this docstring is the place to record the answer"
    )
    assert not isinstance(anything.value, AssertionError)
