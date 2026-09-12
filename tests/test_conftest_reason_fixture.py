"""An OUTSIDE fixture for `classify_git_probe()`'s reason strings.

WHY THIS FILE EXISTS, AND WHY IT IS NOT `tests/test_conftest_git_gate.py`.

`tests/conftest.py`'s `classify_git_probe()` returns human-readable reason
strings that `tests/test_commit_trailers.py`, `tests/test_hook_gate.py` and
`tests/test_line_endings.py` consume, and that `tests/test_hook_interpreter.py`
quotes in prose. That makes the wording a CONTRACT rather than a comment.

The tautology this guards against is recorded in
`tests/test_conftest_git_gate.py`: an arm that advertises byte-identical reasons
by comparing `git_unusable_reason()` against `classify_git_probe()` is comparing
ONE CODE PATH to itself, so it cannot see that path be wrong. A GRADING ARM THAT
CONSULTS THE SAME PREDICATE AS THE THING IT GRADES IS NOT A GRADE.

WHAT THIS FILE IS, MEASURED. It is a SECOND transcription of the same wording in
a separate module, and at the BYTE LEVEL it IS a copy: `EXPECTED_NOT_RUNNABLE`,
`EXPECTED_NOT_A_REPOSITORY` and `EXPECTED_DID_NOT_ANSWER` below compare EQUAL,
string for string, to `tests/test_conftest_git_gate.py`'s
`HAND_TYPED_NOT_RUNNABLE`, `HAND_TYPED_NOT_A_REPOSITORY` and
`HAND_TYPED_DID_NOT_ANSWER` (its lines 499, 504, 511) - compared by running the
comparison, not by eye. A THIRD transcription of the same opening clause lives at
`tests/test_conftest_skip_path_pinned.py:105` as `EXPECTED_128_FRAGMENT`. An
earlier version of this docstring called this file "deliberately NOT a copy" of
its sibling. That was FALSE at the byte level and is corrected here rather than
quietly deleted, because the deleted version of a wrong claim teaches nobody.

THE RESIDUAL RISK, NAMED PLAINLY. Three hand-typed copies of ONE wording, and not
one of the three is derived from a CONSUMER's stated requirement. Three
transcriptions defend against a one-sided EDIT of `tests/conftest.py`; they do
NOT defend against the wording having been wrong from the start. A single wrong
premise about what the consuming modules actually need leaves all three green.

THE SIBLING MODULE IS NOT BLIND TO THE FALLBACK CHAIN. Its
`test_the_detail_text_falls_back_from_stderr_to_stdout_to_a_named_placeholder`
already walks stderr -> stdout -> `no output`, and swapping the chain to
`stdout.strip() or stderr.strip()` in `tests/conftest.py` reddens it - measured,
not assumed. An earlier draft of this docstring claimed that swap was invisible
there. That claim was REFUTED and is likewise recorded rather than deleted. What
this file adds is narrower, and real:

  - the fallback outcomes pinned by FULL-STRING EQUALITY against text authored
    here, where the sibling arm asserts substring CONTAINMENT. `"on stdout" in
    reason` survives any amount of drift in the surrounding sentence, and it
    cannot pin the bracket bytes at all;
  - those same outcomes on the EXIT-128 branch. The sibling arm drives exit 9
    only, so it says nothing about the 128 reason's detail. The `no output`
    fallback is pinned below on BOTH branches;
  - the STRIP OF THE STREAM THE CHAIN CHOOSES. Every other arm here, and every
    arm in the sibling module, feeds a stderr that is ALREADY clean, and the
    blank-stderr arm below pins only the STDOUT half of the strip. So
    `stderr if stderr.strip() else (stdout.strip() or "no output")` - a mutation
    that TESTS with `.strip()` and then interpolates the RAW stream - left the
    whole `tests` suite green, measured 2026-09-12 by applying it. git ends its
    messages with a newline, so that mutation puts one inside a reason that
    `require_git_repository` hands to `pytest.skip()`, where it breaks the
    one-line short summary a reader scans to find out why a guard did not run.
    `test_the_detail_chain_strips_the_stream_it_chooses` below is the only arm
    measured in this tree that carries a trailing newline on a NON-BLANK stream
    INTO the detail chain, and it kills that mutation. The exit-0 arm below
    carries one too, but exit 0 returns before the chain is reached;
  - the FOUR CATEGORY TOKENS as literal spellings typed into THIS file -
    `usable`, `not-runnable`, `not-a-repository`, `did-not-answer`. The sibling
    checks the tokens against `conftest.GIT_PROBE_*` (its lines 282-285), which
    is the same tautology in a smaller frame: respell a token constant in
    `tests/conftest.py` and both sides of that comparison move together. Here the
    spelling is a byte of this file, so a respelling reddens;
  - the RETURNCODE-0 outcome under STREAM NOISE. The bare `is None` result is NOT
    this file's addition - the sibling asserts `usable[1] is None` directly on
    `classify_git_probe` at `tests/test_conftest_git_gate.py:288`, and an earlier
    version of this docstring wrongly claimed that arm as new here. What the two
    exit-0 arms below actually earn is the hand-typed `usable` token above and
    the noisy-stderr input;
  - the classifier called DIRECTLY rather than through `git_unusable_reason()`.
    That helper is `@lru_cache(maxsize=1)` and runs a real `subprocess`; the
    classifier is pure, so nothing here needs a stub, a cache reset, or a
    repository. No arm below locates a repository, so no arm's verdict can be
    perturbed by an exported `GIT_DIR` or `GIT_WORK_TREE`.

THIS FILE DOES NOT SUBSUME `tests/test_conftest_git_gate.py`, AND DOES NOT TRY.
Read against that module, it covers ground no arm below touches: the probe's own
argv, cwd and `capture_output` kwargs (its `EXPECTED_ARGV` at line 68, asserted at
lines 121-129), the skip helpers `require_git_repository` and
`skip_module_without_git` (lines 345-412), and `Skipped` not being an `Exception`
subclass (line 414). Deleting either module loses real coverage.

WHAT IS HAND-TYPED AND WHAT IS SUBSTITUTED AT RUNTIME.

Every byte of the templates below - EVERY BRACKET, EVERY SPACE, every backtick,
every comma - was typed into this file by hand from the source. Nothing here is
imported from `tests/conftest.py`, built by calling a `conftest` helper, or read
out of `tests/conftest.py` at runtime.

The four `{...}` placeholders are the ONLY runtime substitutions, and each spans
the narrowest possible run of characters:

  - `{root}`       the repository path. Machine-dependent, so pinning it would
                   pin this checkout rather than the contract. It is derived HERE
                   from this file's own `__file__` - the same two-parent walk the
                   audited module does - and is NOT read from `conftest.REPO_ROOT`,
                   so a change to that expression is not silently absorbed.
  - `{exec_error}` the already-formatted `"OSError: message"` text, an INPUT to
                   the classifier and therefore chosen by the caller below.
  - `{returncode}` the non-128 exit code, likewise an input.
  - `{detail}`     the resolved detail text, likewise derived from inputs.

The parentheses AROUND `{exec_error}`, `{returncode}`'s trailing `({detail})` and
the `({detail})` in the exit-128 reason are LITERAL BYTES OF THIS FILE. Changing
`(detail)` to `[detail]` or `<detail>` in `tests/conftest.py` reddens here.

THE CEILING OF THIS FILE. It pins the reason TEXT, the four token spellings and
the `None`. It says nothing about whether SKIPPING is the right disposition for
any of these outcomes - `tests/test_conftest_skip_path_pinned.py` holds that
question - and nothing about the category tokens beyond the four spellings
asserted below.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests import conftest

#: This repository's root, derived from THIS file rather than from the module
#: under audit. `tests/test_conftest_reason_fixture.py` -> `tests/` -> the root,
#: which is the same two-parent walk `tests/conftest.py` performs. Deriving it
#: here rather than importing `conftest.REPO_ROOT` keeps the substitution honest:
#: if that expression ever changed, this file would disagree rather than follow.
REPO_ROOT = Path(__file__).resolve().parent.parent

#: The four category tokens, TYPED BY HAND. Not imported from `conftest`, for the
#: same reason the reason strings are not: a constant read out of the file under
#: audit grades nothing.
TOKEN_USABLE = "usable"
TOKEN_NOT_RUNNABLE = "not-runnable"
TOKEN_NOT_A_REPOSITORY = "not-a-repository"
TOKEN_DID_NOT_ANSWER = "did-not-answer"

#: The literal the classifier falls back to when neither stream carried text.
#: Typed by hand; it is part of the same contract as the surrounding prose.
NO_OUTPUT_TEXT = "no output"

EXPECTED_NOT_RUNNABLE = (
    "git is not runnable on this machine ({exec_error}), so trackedness cannot be "
    "established for {root} and this guard is SKIPPED rather than passed"
)

EXPECTED_NOT_A_REPOSITORY = (
    "this tree is not a git repository, so trackedness cannot be established and this "
    "guard is SKIPPED rather than passed: `git rev-parse --git-dir` in {root} exited 128 "
    "({detail}). That is the normal state of a Download-ZIP, sdist or `git archive` copy "
    "- clone the repository to enforce this guard"
)

EXPECTED_DID_NOT_ANSWER = (
    "git is present but did not answer for {root}, so trackedness cannot be established "
    "and this guard is SKIPPED rather than passed: `git rev-parse --git-dir` exited "
    "{returncode} ({detail})"
)


def _not_runnable(exec_error: str) -> str:
    return EXPECTED_NOT_RUNNABLE.format(exec_error=exec_error, root=REPO_ROOT)


def _not_a_repository(detail: str) -> str:
    return EXPECTED_NOT_A_REPOSITORY.format(root=REPO_ROOT, detail=detail)


def _did_not_answer(returncode: int, detail: str) -> str:
    return EXPECTED_DID_NOT_ANSWER.format(root=REPO_ROOT, returncode=returncode, detail=detail)


def _drift(expected: str, actual: object) -> str:
    return (
        "a reason string in tests/conftest.py drifted from the wording typed by hand in "
        "tests/test_conftest_reason_fixture.py. Four modules under tests/ consume this text "
        "and tests/test_hook_interpreter.py quotes it in prose, so it is a contract and not "
        f"a comment.\n  expected: {expected!r}\n  actual:   {actual!r}"
    )


def test_the_exec_error_outcome_matches_the_reason_typed_by_hand_here() -> None:
    """`exec_error` set, `returncode` None: git could not be run at all."""
    exec_error = "FileNotFoundError: [Errno 2] No such file or directory: 'git'"
    category, reason = conftest.classify_git_probe(None, "", "", exec_error)

    assert category == TOKEN_NOT_RUNNABLE
    expected = _not_runnable(exec_error)
    assert reason == expected, _drift(expected, reason)


def test_the_exec_error_outcome_ignores_both_streams() -> None:
    """`exec_error` short-circuits BEFORE the `detail` chain is consulted.

    The branch returns before `detail` is computed, so text on either stream must
    not reach the reason. Moving the `exec_error` test below the `detail` line, or
    threading a stream into this reason, reddens here.
    """
    exec_error = "OSError: exec format error"
    _, reason = conftest.classify_git_probe(None, "loud stdout", "loud stderr", exec_error)

    expected = _not_runnable(exec_error)
    assert reason == expected, _drift(expected, reason)
    assert reason is not None
    assert "loud stdout" not in reason
    assert "loud stderr" not in reason


def test_the_returncode_zero_outcome_carries_no_reason_at_all() -> None:
    """Exit 0 is the usable outcome, its token is `usable` and its reason is `None`.

    The `is None` half is also asserted by the sibling module at
    `tests/test_conftest_git_gate.py:288`, so it is not what this arm earns its
    place on - the HAND-TYPED token spelling is. The sibling compares the token
    against `conftest.GIT_PROBE_USABLE`, which follows a respelling of that
    constant; `TOKEN_USABLE` here does not.

    The reason check stays `is None` rather than a falsy check regardless: an
    empty string would satisfy every `if reason is not None` guard in the
    consuming modules - `require_git_repository` would call `pytest.skip("")` and
    every git-dependent guard in this directory would evaporate while the suite
    still read green.
    """
    category, reason = conftest.classify_git_probe(0, ".git\n", "", None)

    assert category == TOKEN_USABLE
    assert reason is None, _drift("None", reason)


def test_the_returncode_zero_outcome_stays_none_even_with_noise_on_stderr() -> None:
    """Exit 0 wins over stream content. git warns on stderr and still succeeds."""
    _, reason = conftest.classify_git_probe(0, ".git\n", "warning: something cosmetic\n", None)

    assert reason is None, _drift("None", reason)


def test_the_128_outcome_matches_the_reason_typed_by_hand_here() -> None:
    """Exit 128 is git's own code for `not a repository`."""
    detail = "fatal: not a git repository (or any of the parent directories): .git"
    category, reason = conftest.classify_git_probe(128, "", detail, None)

    assert category == TOKEN_NOT_A_REPOSITORY
    expected = _not_a_repository(detail)
    assert reason == expected, _drift(expected, reason)


def test_the_non_128_non_zero_outcome_matches_the_reason_typed_by_hand_here() -> None:
    """Any other non-zero exit: git is present but did not answer.

    This branch was separated from its 128 neighbour by no test at all before the
    extraction, so it could have been deleted into that neighbour with the whole
    suite green. The returncode is interpolated, so the arm also says the code is
    reported rather than swallowed.
    """
    detail = "error: bad config line 3"
    category, reason = conftest.classify_git_probe(7, "", detail, None)

    assert category == TOKEN_DID_NOT_ANSWER
    expected = _did_not_answer(7, detail)
    assert reason == expected, _drift(expected, reason)


@pytest.mark.parametrize("returncode", [1, 2, 7, 127, 129, -1])
def test_every_other_non_zero_returncode_reaches_the_did_not_answer_reason(returncode: int) -> None:
    """The non-128 branch is the DEFAULT, not a list of enumerated codes.

    The neighbour arm above pins one code. This one says the branch is reached for
    codes on both sides of 128 and for a negative code - a POSIX signal death is
    reported as a negative returncode by `subprocess`, and it must not be mistaken
    for the usable outcome.
    """
    detail = "some failure text"
    category, reason = conftest.classify_git_probe(returncode, "", detail, None)

    assert category == TOKEN_DID_NOT_ANSWER
    expected = _did_not_answer(returncode, detail)
    assert reason == expected, _drift(expected, reason)


def test_the_detail_chain_prefers_stderr_over_stdout_in_the_128_reason() -> None:
    """`stderr.strip() or stdout.strip() or "no output"` - stderr FIRST.

    Both streams carry text, so a swapped chain returns the stdout text and this
    reddens. tests/test_conftest_git_gate.py reddens for that swap too - measured;
    what is new here is the FULL-STRING equality and the 128 branch, since that
    module's arm checks substring containment on exit 9 only.
    """
    _, reason = conftest.classify_git_probe(128, "text from stdout", "text from stderr", None)

    expected = _not_a_repository("text from stderr")
    assert reason == expected, _drift(expected, reason)


@pytest.mark.parametrize("blank_stderr", ["", "   ", "\n", " \t\n "])
def test_the_detail_chain_falls_back_to_stdout_when_stderr_is_blank(blank_stderr: str) -> None:
    """A WHITESPACE-ONLY stderr is blank, because the chain calls `.strip()`.

    `stderr or stdout` and `stderr.strip() or stdout.strip()` differ exactly here:
    the first picks a stderr of `"\\n"` and renders a reason with a newline inside
    it, the second falls through to stdout. This arm pins the second.
    """
    _, reason = conftest.classify_git_probe(128, "  text from stdout  ", blank_stderr, None)

    expected = _not_a_repository("text from stdout")
    assert reason == expected, _drift(expected, reason)



def test_the_detail_chain_strips_the_stream_it_chooses() -> None:
    """The CHOSEN stream is stripped, not merely TESTED with `.strip()`.

    git terminates its own messages with a newline, so a real exit-128 stderr
    reaches the classifier with a trailing one. Measured 2026-09-12, no other arm
    in this file or its sibling feeds such a stream INTO the detail chain: the
    exit-0 arm above feeds one and returns before the chain, and the blank-stderr
    arms feed whitespace only. A gate cannot fail if its fixture excludes the
    defect, so the fixture here carries the newline deliberately.

    The mutation this arm exists to kill keeps the `.strip()` as a TEST and drops
    it from the VALUE: `stderr if stderr.strip() else (stdout.strip() or
    "no output")`. It agrees with the real chain on every already-clean stderr,
    on every blank stderr, and on both-streams-blank, so it survives every other
    arm in this file. Measured 2026-09-12: applied to `tests/conftest.py` it left
    the whole `tests` suite green.

    The consequence is not cosmetic. `require_git_repository()` passes this text
    to `pytest.skip()`, and a newline inside it splits the one-line short summary
    that tells a reader why a guard was skipped rather than passed.

    Both halves are asserted. The `==` pins the WHOLE rendered reason, so the arm
    is about the value produced from a specific input rather than about its shape;
    the newline assertion names the defect directly for whoever reads the failure.
    """
    clean_detail = "fatal: not a git repository (or any of the parent directories): .git"

    _, reason = conftest.classify_git_probe(128, "", clean_detail + "\n", None)

    expected = _not_a_repository(clean_detail)
    assert reason == expected, _drift(expected, reason)
    assert reason is not None
    assert "\n" not in reason, (
        "the chosen stream reached the reason unstripped, so git's trailing newline is now "
        "inside a string that `pytest.skip()` renders as a one-line summary: "
        f"{reason!r}"
    )


@pytest.mark.parametrize("returncode", [128, 7])
def test_the_detail_chain_falls_back_to_the_literal_no_output_text(returncode: int) -> None:
    """Both streams blank: the detail is the literal `no output`, on BOTH branches.

    The alternative - an empty detail - renders as `()` and tells a reader nothing
    about whether git said nothing or the guard lost the message.
    """
    _, reason = conftest.classify_git_probe(returncode, "   ", "\n", None)

    expected = (
        _not_a_repository(NO_OUTPUT_TEXT)
        if returncode == 128
        else _did_not_answer(returncode, NO_OUTPUT_TEXT)
    )
    assert reason == expected, _drift(expected, reason)


# ---------------------------------------------------------------------------
# NON-VACUITY. The arms above are all `==` against templates authored here, so
# a template that rendered empty, or three templates that rendered to one
# string, would satisfy them while pinning nothing. The two arms below prove the
# expectations are real and are literals of this file.
#
# The other half of non-vacuity - that the `==` DISCRIMINATES on the delimiter
# SHAPE rather than on one wrong spelling - is not restated here. It lives in
# `tests/test_conftest_git_gate.py`'s `test_the_census_rejects_every_wrong_delimiter_shape`
# (its line 611) with the surviving-neighbour arm
# `test_the_census_accepts_the_delimiter_shape_actually_in_use` (its line 647),
# against a byte-identical template. A second copy of that sweep here killed no
# mutant the sibling's copy did not already kill.
# ---------------------------------------------------------------------------


def test_the_hand_typed_reasons_render_non_empty_and_pairwise_distinct() -> None:
    """None of the three templates renders empty, and no two render alike."""
    rendered = [
        _not_runnable("OSError: no exec for you"),
        _not_a_repository("boom"),
        _did_not_answer(7, "boom"),
    ]

    assert all(text.strip() for text in rendered), f"a hand-typed reason rendered empty: {rendered}"
    assert len(set(rendered)) == 3, f"the three hand-typed reasons must be pairwise distinct: {rendered}"


def test_this_file_does_not_read_its_expectations_out_of_the_file_it_audits() -> None:
    """The whole point, asserted rather than merely promised in the docstring.

    Two claims. First, the templates are not equal to anything the audited module
    exposes as a constant - there is no reason-string constant in `tests/conftest.py`
    to import, and if one ever appeared, importing it instead of typing the text
    would silently re-open the tautology. Second, the source of THIS file contains
    the contract text as a literal, which is what makes the `==` above a grade.
    """
    source = Path(__file__).read_text(encoding="utf-8")

    for fragment in (
        "git is not runnable on this machine ({exec_error}), so trackedness cannot be ",
        "guard is SKIPPED rather than passed: `git rev-parse --git-dir` in {root} exited 128 ",
        "git is present but did not answer for {root}, so trackedness cannot be established ",
    ):
        assert fragment in source, f"the hand-typed contract text is no longer a literal here: {fragment!r}"

    conftest_source = Path(conftest.__file__).read_text(encoding="utf-8")
    assert "EXPECTED_NOT_A_REPOSITORY" not in conftest_source, (
        "tests/conftest.py now names this file's fixture, which would mean the expectation "
        "and the implementation share a source"
    )
