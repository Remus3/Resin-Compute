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

THE GIT GATE HERE IS RUN-TIME AND PARTIAL, AND BOTH HALVES OF THAT WERE MEASURED.

This module was UNGATED until 2026-09-11. With `PATH` replaced by one empty
directory and both lookups verified empty - `shutil.which` returning None and
`subprocess.run(["git", ...])` raising `FileNotFoundError` - it reported
`2 failed, 3 passed` at exit 1:

  - `test_git_returns_str_on_success` - `_git` catches the `OSError` and returns
    `None`, so `isinstance(None, str)` is False. Git is reached inside
    `tools/precommit_gate.py`, a CHILD module, so no AST walk over THIS file can
    see that dependency; only the gate call now in its body records it.
  - `test_check_staged_passes_a_clean_repo_with_nothing_staged` - `_init_repo`
    shells `git init` directly and the `FileNotFoundError` escapes.

`require_git_repository()` - the RUN-time per-test helper - is therefore called
in exactly those two places, and `skip_module_without_git()` is NOT used: git is
reached from inside test bodies, never at import time, and an import-time
whole-module skip would take the other three tests uncollected for a dependency
they do not have.

THE OTHER THREE ARE DELIBERATELY LEFT UNGATED, and the reason is that their
assertions stay TRUE with git absent rather than merely unexercised. Each pins
the shape of a FAILED read - `None` rather than `""`, rc 1 rather than rc 0 -
and `_git` answers `None` for an `OSError` by the same `except` clause it
answers `None` for exit 128. What changes with git absent is WHICH branch of
`_git` produced the `None`, not whether the contract held. Gating them would
delete three live guards to buy nothing. If `_git` ever stops catching
`OSError`, they go RED under an absent git - which is the correct answer, not a
regression in this gating.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pytest

from tests.conftest import require_git_repository

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
    """A real repo with a real commit, so `git diff --cached` is answerable.

    THE GATE SITS HERE RATHER THAN IN THE CALLER, which is the shape
    `tests/conftest.py` documents for `require_git_repository()`: raise the skip
    at the single point where the dependency is real. Without it the three
    `subprocess.run(["git", ...])` calls below raise `FileNotFoundError` on a
    host with no git and the caller reports a FAILURE rather than a skip.
    """
    require_git_repository()
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
    """The arm that says the None is about FAILURE and not about everything.

    THE ONLY ARM IN THIS MODULE WHOSE GIT DEPENDENCY IS INVISIBLE TO AN AST WALK
    OVER THIS FILE. It launches nothing itself - `gate._git` does, inside
    `tools/precommit_gate.py` - so the census-backed git half of the derivation
    in `tests/test_conftest_git_gate_sites.py` cannot see it and named only the
    OTHER of this module's two failing nodes. The gate call is what puts this
    node into the derived population, which is the gate half of that union doing
    exactly the job it is there for.
    """
    require_git_repository()
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


# ---------------------------------------------------------------------------
# ARGUMENT REFUSAL. A second defect of the SAME shape as the corpus read above:
# an input the tool did not understand reaching the hook lane and exiting 0.
#
# LL filed the sharpest statement of it on 2026-09-08. Its gate invoked with a
# ONE-CHARACTER SLIP in a flag exited 0 and printed NOTHING: only the exact
# token was recognised, anything else FELL THROUGH to the hook path, found no
# payload on stdin, and returned 0. The real invocation exits 0 on a clean
# repository too, so a git hook - which reads nothing but the exit code - could
# not tell a running gate from a gate that a typo had switched off.
#
# THIS TREE ALREADY REFUSED AN UNRECOGNISED LEADING FLAG. Measured at e9b4542
# before any edit here: `--scan-file README.md` and `--frobnicate` both exited 1
# naming the argument. `test_an_unrecognised_leading_flag_is_refused` below is
# therefore a REGRESSION PIN on a property that already held, not a new claim -
# it is here so the property cannot be deleted silently.
#
# THREE RESIDUAL PATHS DID fall through, all three measured at that same SHA,
# and they are what the other arms are about:
#
#   1. `--expect-count 5` with NO scan mode following it. The pair is consumed,
#      `args` goes empty, the `if args:` unknown-argument branch is skipped
#      because there is nothing left to be unknown, and control reaches the
#      stdin lane. rc 0, empty stdout, empty stderr - and the ANTI-VACUITY
#      count, whose entire job is to refuse a sweep that selected the wrong
#      number of files, was discarded without a word.
#   2. A single-value mode flag with a trailing token: `--message-file README.md
#      --frobnicate` scanned README.md and threw the slip away. rc 0. Every
#      single-value mode read args[1] and never looked at args[2:].
#   3. No arguments and NO payload on stdin. rc 0, silent. This is the vacuous
#      manual run already recorded in docs/LEDGER.md, and it is why "I ran the
#      gate" by hand has never meant anything here.
#
# THE DECISION ON CASE 3, stated in the module docstring of
# tools/precommit_gate.py as well: a payload on stdin is REQUIRED for the staged
# lane. .githooks/pre-commit always supplies one - it is literally
# `echo "git commit" | ... precommit_gate.py` - so no legitimate caller in this
# tree invokes the gate with an empty stdin. A command string that is present
# and is NOT a commit still exits 0: that input was understood, and the answer
# is a genuine no-op. The arms below pin both halves of that, because a refusal
# that also refused the hook's own no-op call would wedge the repo.
#
# EXIT CODE. 1, deliberately, not 2. The module contract is "any finding exits
# 1", the three hook bodies all read `|| exit 1`, and this tree has a recorded
# finding that EXIT 2 IS NOT SELF-EVIDENCING - a module whose syntax is broken
# and a tool that deliberately refused to start are both exit 2, so the number
# cannot carry the meaning. Every arm here therefore asserts on the SPOKEN
# refusal as well as on the number.

_REFUSAL = "precommit_gate REFUSED"


def _run(args: list[str], stdin: bytes | None = b"") -> subprocess.CompletedProcess:
    """Invoke the gate as a real process, which is what a hook line does.

    `stdin=b""` is an open but empty stream; `stdin=None` is no stream at all.
    Both are silent-pass shapes and both are measured.

    NOT `gate.main([...])`: pytest replaces `sys.stdin` with an object whose
    `read()` raises, so an in-process call cannot exercise the stdin lane at
    all - and the stdin lane is exactly where the fall-through lands.
    """
    argv = [sys.executable, str(TOOLS / "precommit_gate.py"), *args]
    if stdin is None:
        return subprocess.run(
            argv,
            cwd=str(REPO_ROOT),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=120,
        )
    return subprocess.run(
        argv, cwd=str(REPO_ROOT), input=stdin, capture_output=True, timeout=120,
    )


def _err(out: subprocess.CompletedProcess) -> str:
    return out.stderr.decode("utf-8", "replace")


def test_an_unrecognised_leading_flag_is_refused():
    """The regression pin. This property held at e9b4542; it must keep holding."""
    for slip in ("--scan-file", "--frobnicate"):
        out = _run([slip, "README.md"])
        assert out.returncode != 0, (
            f"{slip} exited 0 - a one-character slip switched the gate off and "
            "reported success"
        )
        assert slip in _err(out), f"refused {slip} without naming it: {_err(out)!r}"


def test_expect_count_without_a_scan_mode_is_refused_not_silently_dropped():
    """Case 1. The anti-vacuity count discarded, then rc 0 from the stdin lane."""
    out = _run(["--expect-count", "5"])
    assert out.returncode != 0, (
        "--expect-count with no scan mode exited 0: the count was discarded and "
        "control fell through to the stdin lane, which scanned nothing"
    )
    assert _REFUSAL in _err(out), f"non-zero but not SPOKEN as a refusal: {_err(out)!r}"
    assert "--expect-count" in _err(out)


def test_a_mode_flag_with_a_trailing_unrecognised_token_is_refused():
    """Case 2. args[1] was read and args[2:] was never looked at."""
    out = _run(["--message-file", "README.md", "--frobnicate"])
    assert out.returncode != 0, (
        "a trailing unrecognised token after --message-file exited 0 - the slip "
        "was swallowed and the caller was told the scan passed"
    )
    assert _REFUSAL in _err(out), f"not spoken as a refusal: {_err(out)!r}"
    assert "--frobnicate" in _err(out), f"refused without naming it: {_err(out)!r}"


def test_no_arguments_and_no_stdin_payload_is_refused():
    """Case 3, both stream shapes: an empty stream and no stream at all."""
    for label, stream in (("empty stdin", b""), ("no stdin at all", None)):
        out = _run([], stdin=stream)
        assert out.returncode != 0, (
            f"bare with {label} exited 0 having scanned nothing - every manual "
            "run of this gate was vacuous"
        )
        assert _REFUSAL in _err(out), (
            f"bare with {label} refused in silence: {_err(out)!r}"
        )


def test_a_non_commit_command_on_stdin_still_exits_zero():
    """THE LANE THAT MUST NOT CHANGE, and the non-vacuity arm for the one above.

    Without this, the refusal could be implemented as "no arguments always
    fails" and every no-op hook invocation in the tree would start blocking.
    The input here is present and understood; the answer is a genuine no-op.
    """
    out = _run([], stdin=b"git status\n")
    assert out.returncode == 0, f"a non-commit command string was refused: {_err(out)!r}"


def test_a_named_mode_still_scans(tmp_path):
    """The other non-vacuity arm: the refusal did not disable the scan modes."""
    clean = tmp_path / "clean.txt"
    clean.write_bytes(b"a clean ascii line\n")
    out = _run(["--scan-files", str(clean)])
    assert out.returncode == 0, f"--scan-files on a clean file failed: {_err(out)!r}"
    assert b"1 file(s) scanned" in out.stdout, (
        f"--scan-files reported no scan: {out.stdout!r}"
    )


# ---------------------------------------------------------------------------
# THE SUBJECT REPORT. A THIRD defect of the SAME family as the two above, and
# the one neither of them closed.
#
# The corpus arms fixed `None` vs `{}`: an UNREAD corpus now blocks, and a READ
# but empty one still passes. The refusal arms fixed an input the tool did not
# UNDERSTAND reaching the hook lane. What is left is an input the tool
# understood perfectly, over a corpus it really did read, that happens to be
# EMPTY - and `_check_staged` answered it by returning 0 having written not one
# byte anywhere. `echo "git commit" | python tools/precommit_gate.py` in a tree
# with a clean index and the same line in a tree with forty staged files
# produced BYTE-IDENTICAL output: nothing at all, rc 0.
#
# WHY "BLOCK ON AN EMPTY INDEX" IS THE WRONG ANSWER, and this is a DECISION
# rather than a deduction. An empty staged corpus is a genuine fact about the
# tree, `git commit --allow-empty` is a legitimate invocation that fires
# .githooks/pre-commit with exactly that corpus, and
# `test_check_staged_passes_a_clean_repo_with_nothing_staged` above already
# pins the pass. Blocking would wedge the hook and would contradict
# `_staged_added`'s own recorded distinction. The defect is not that emptiness
# PASSES; it is that emptiness is INVISIBLE.
#
# The scan lanes solved this for themselves and the staged lane never got the
# same treatment: `_check_scan_files` prints `selected= scanned= exempt=` on
# every clean exit, so a zero there is legible. The fix gives the staged lane
# the same arithmetic, on EVERY exit including a blocking one.
#
# THE NON-VACUITY SHAPE THESE ARMS USE. A single arm asserting "some report
# line is present" would be a FORMAT arm, and this tree has a recorded finding
# that a shape arm pins format and not input: a mutant printing a fixed
# `staged=0 added-lines=0` without ever consulting the corpus would satisfy it.
# So every arm below parses the two integers back out and compares them against
# WHAT THE FIXTURE ACTUALLY STAGED - zero files in one, two files and seven
# added lines in another, one file and one added line in a third. No constant
# satisfies all three.
# ---------------------------------------------------------------------------

#: Parsed rather than matched whole, so the arms assert on the COUNTS and not
#: on the sentence carrying them.
_STAGED_SUBJECT = re.compile(rb"precommit_gate: staged=(\d+) added-lines=(\d+)")


def _subject(out: subprocess.CompletedProcess) -> tuple[int, int]:
    """(files, added lines) as the gate REPORTED them, or fail saying so."""
    match = _STAGED_SUBJECT.search(out.stdout)
    assert match is not None, (
        "the staged lane stated no subject at all, so a corpus of zero files "
        "and a corpus of forty are indistinguishable to the caller. "
        f"stdout={out.stdout!r} stderr={out.stderr!r}"
    )
    return int(match.group(1)), int(match.group(2))


def _commit_stdin(root: pathlib.Path) -> bytes:
    """The command string the staged lane really carries, with a -C root."""
    return f'git -C "{root}" commit -m x'.encode()


def _stage(root: pathlib.Path, name: str, payload: bytes) -> None:
    """Write a file and put it in the index of the throwaway repo."""
    (root / name).write_bytes(payload)
    subprocess.run(
        ["git", "add", "--", name], cwd=str(root), capture_output=True, timeout=60,
    )


def test_an_empty_staged_corpus_states_its_subject_instead_of_passing_silently(
    tmp_path,
):
    """THE DEFECT ITSELF, reinstated: a real repo whose index is really clean.

    No monkeypatch and no stub - `git diff --cached` genuinely answers with an
    empty diff here, which is the `{}` the arm above proves must keep passing.
    What must change is that the pass now SAYS the corpus was empty.
    """
    _init_repo(tmp_path)
    out = _run([], stdin=_commit_stdin(tmp_path))
    assert out.returncode == 0, (
        "a clean index was blocked, which would wedge `git commit "
        f"--allow-empty` and every hook firing on one: {_err(out)!r}"
    )
    files, lines = _subject(out)
    assert (files, lines) == (0, 0), (
        f"reported staged={files} added-lines={lines} for an index holding "
        "nothing - the report is not reading the corpus"
    )


def test_the_subject_report_counts_the_fixture_and_not_a_constant(tmp_path):
    """THE NON-VACUITY ARM. A hardcoded zero cannot survive this one.

    Two files, three added lines and four, so both integers are pinned to a
    fixture value no constant shared with the arm above can satisfy. `.txt` on
    purpose: the py_compile and net-new-ruff halves key on `.py` and would
    otherwise decide this arm's exit code for it.
    """
    _init_repo(tmp_path)
    _stage(tmp_path, "alpha.txt", b"one\ntwo\nthree\n")
    _stage(tmp_path, "beta.txt", b"four\nfive\nsix\nseven\n")
    out = _run([], stdin=_commit_stdin(tmp_path))
    assert out.returncode == 0, f"two clean ASCII files were blocked: {_err(out)!r}"
    files, lines = _subject(out)
    assert (files, lines) == (2, 7), (
        f"reported staged={files} added-lines={lines} for a fixture staging 2 "
        "files and 7 added lines"
    )


def test_the_subject_is_stated_on_a_blocking_exit_too(tmp_path):
    """The report is UNCONDITIONAL, not bolted onto the success path.

    A gate that states its subject only when it passes still leaves a blocked
    caller unable to tell how much was looked at. The banned glyph is written
    as raw UTF-8 BYTES from ASCII escapes, because a literal em-dash in this
    file would make the module violate the very rule it is testing.
    """
    _init_repo(tmp_path)
    _stage(tmp_path, "bad.txt", b"a \xe2\x80\x94 b\n")
    out = _run([], stdin=_commit_stdin(tmp_path))
    assert out.returncode == 1, (
        f"a staged em-dash was not blocked: {out.stdout!r} {_err(out)!r}"
    )
    files, lines = _subject(out)
    assert (files, lines) == (1, 1), (
        f"a BLOCKING run reported staged={files} added-lines={lines} for a "
        "fixture staging 1 file and 1 added line"
    )


def test_the_non_commit_lane_says_it_scanned_nothing():
    """The SIBLING case, same root cause: another `return 0` written in silence.

    `git status` on stdin is understood and is a genuine no-op, and
    `test_a_non_commit_command_on_stdin_still_exits_zero` above pins that it
    keeps exiting 0. But rc 0 with empty output carries the same ambiguity: a
    caller reading it cannot tell a gate that DECLINED to scan from one that
    scanned and found nothing. It must say which.

    The second clause is the direction arm. Without it the lane could satisfy
    the first by printing a staged subject it never read, which would be a
    worse lie than the silence.
    """
    out = _run([], stdin=b"git status\n")
    assert out.returncode == 0, f"a non-commit command was refused: {_err(out)!r}"
    assert out.stdout.strip(), (
        "the non-commit lane exited 0 having written nothing, so declining to "
        "scan and scanning cleanly are indistinguishable"
    )
    assert _STAGED_SUBJECT.search(out.stdout) is None, (
        f"the non-commit lane reported a STAGED subject it never read: "
        f"{out.stdout!r}"
    )
