"""The working tree must match the line endings `.gitattributes` declares.

WHY A BYTE CHECK ON DISK, AND WHY A DIFF CHECK WOULD BE VACUOUS.

`.gitattributes` sets `* text=auto eol=lf` plus explicit `eol=lf` for every
source suffix, and its own header says that forcing this "pins the bytes in the
repo AND in the working tree, which overrides autocrlf so neither can recur".

The first half of that is enforced by git itself: content is normalised to LF on
the way into the index, so `git diff` on a CRLF working file shows NOTHING but a
warning. The second half was enforced by nothing at all, and drifted - measured
2026-09-06, 16 of 72 tracked `.py` files carried CRLF on disk while every diff
in the repository looked clean. Editors and tooling that write CRLF on save
produce exactly this, silently, forever.

So the only meaningful check is the one below: read the BYTES off disk. A test
that compared the index to the working tree would agree with itself and pass
while the drift accumulated, which is precisely what happened.

Sibling-C paid for the CRLF class of bug twice, including 21 tracked `.py`
files with doubled CR endings, and `.gitattributes` cites that as the reason the
policy exists. The `.githooks/` shims are the sharper case: they are `#!/bin/sh`
scripts, and a CRLF shebang makes the kernel look for an interpreter named
"/bin/sh\r", so the whole commit-time gate goes silently absent.

NOT A CI TEST IN PRACTICE. A fresh checkout on the Linux runner honours
`eol=lf`, so this passes there by construction. Its value is local, on the
Windows machines where the drift is actually produced.
"""
from __future__ import annotations

import ast
import subprocess
import typing
from pathlib import Path

import pytest

from tests.conftest import git_unusable_reason
from tests.test_guard_worktree_exclusion import swept_files

REPO_ROOT = Path(__file__).resolve().parent.parent

CRLF = b"\r\n"

# The exception pytest.skip raises. Named because the arms below must be able to
# say "anything BUT a skip" - `pytest.raises(Failed)` would be the narrower and
# weaker claim, since a repair that turned the skip into an unrelated crash
# would satisfy neither and must still count as progress away from a silent
# skip.
_SKIPPED = pytest.skip.Exception

# The exception pytest.fail raises. Named for the same reason: the check-attr
# arms below must assert the outcome was a FAILURE specifically, because "not a
# skip" alone would also be satisfied by an unrelated TypeError from a parser
# that crashed on the stream instead of judging it.
_FAILED = pytest.fail.Exception


def _require_a_repository_to_break() -> None:
    """Skip an INJECTION arm where git does not enumerate this corpus anyway.

    THREE DISPOSITIONS, NOT TWO. Every arm that plants a broken tool below
    conflated the second of these with the third, and that is what made this
    file red on a legitimate machine:

      1. the tool ran and the answer is genuinely nothing -> skip, reason TRUE
      2. the tool ran and something went wrong            -> FAIL
      3. the tool cannot answer about THIS tree at all    -> skip, reason TRUE

    Those arms plant case 2 and then assert the caller did not report a SKIP.
    Where the caller never reaches the injected tool, the not-a-skip assertion
    fires against an honest answer and reddens a machine where nothing whatever
    is wrong.

    THE GATE USED TO ASK THE WRONG QUESTION, AND THAT WAS THE DEFECT THAT
    MATTERED. It asked `git_unusable_reason()`, which is
    `git rev-parse --git-dir`, and that WALKS UP THE DIRECTORY TREE. A
    Download-ZIP, sdist or `git archive` copy extracted anywhere INSIDE another
    repository gets exit 0 from it, so the gate never fired - while
    `git ls-files` legitimately reported nothing at all about THIS tree.

    MEASURED 2026-09-08, a copy of this worktree with its `.git` removed placed
    inside a freshly initialised outer repository:
    `git rev-parse --git-dir` answered with the OUTER repository,
    `git ls-files | wc -l` printed 0, `git_unusable_reason()` returned None,
    and `python -m pytest tests/test_line_endings.py -rA` gave 20 failed, 16
    passed, ZERO skipped, EXIT=1. The casualties included the CRLF guard itself
    and both positive controls.

    THE QUESTION THESE ARMS NEED IS NOT "is there a repository above this
    directory". IT IS "DOES GIT ENUMERATE THIS CORPUS", and the two differ in
    exactly the outer-repository case. `_corpus_gate_reason()` asks the second,
    off the real unmodified `git ls-files` measured at import.

    A PROXY CANNOT BE RIGHT HERE, and that is why this consults the real
    measurement rather than a cheaper stand-in. Every proxy for "git enumerates
    this corpus" is some other question that happens to agree in the worlds
    somebody thought of; the outer-repository world is the one nobody did, and
    a fourth patch to a fourth proxy would be the same bet again.

    So an injection arm first establishes that the UNBROKEN tool could have
    answered. Where it could not, the arm has no case-2 input to grade and says
    so rather than converting somebody else's correct skip into a failure.

    This does NOT weaken case 2. Wherever git does enumerate this tree the gate
    is a no-op, and test_no_corpus_helper_skips_while_the_corpus_gate_is_closed
    reddens if it is ever anything else there.
    """
    reason = _corpus_gate_reason()
    if reason is not None:
        pytest.skip(
            "this arm injects a BROKEN git to prove the caller FAILS rather than "
            "skipping, and git does not enumerate this corpus even unbroken - the "
            "caller would skip for a reason that is true whether or not anything "
            f"was injected, so there is nothing to grade: {reason}"
        )


class _Enumeration(typing.NamedTuple):
    """What `git ls-files` said, with FAILURE and EMPTINESS held apart.

    A bare `list[str]` cannot carry the difference between "git enumerated the
    tree and it holds no such file" and "git never answered", and the callers
    below turn the second into a skip that reads exactly like the first.
    """

    status: str  # "OK" | "FAILED" | "UNAVAILABLE"
    files: tuple[str, ...]
    reason: str


# A LITERAL, and it must stay one. Sizing this from `len(_tracked_files())` -
# the obvious-looking "the tree has at least as many files as the tree has" -
# would make the floor agree with whatever the enumeration returned, including
# nothing. A fixture sized from the value under test is an amplifier, not a
# check. 50 is far below the 195 paths measured 2026-09-08 and far above the
# zero a broken enumeration returns, so the interval where it fires is wide and
# non-empty; test_the_floor_is_not_decorative_and_can_actually_fail proves that
# rather than asserting it.
#
# THE ONE LITERAL, and it must stay the only one. Every other arm in this file
# refers to this name, so nothing here can drift away from it - which also
# means every arm moves WITH it and none of them can see it drift. Measured
# 2026-09-08, raising it to 150 and to 190 both left this file green;
# test_the_floor_keeps_wide_clearance_below_the_real_tree closes that by
# asserting the interval this value has to sit in rather than the value.
_MIN_TRACKED_FILES = 50

# THE FLOOR ALONE CANNOT SEE A PARTIAL ENUMERATION. A `git ls-files` narrowed by
# a pathspec, a sparse checkout, or a cwd that landed in a subdirectory can
# return 60 plausible paths, clear the floor, and still be missing every `.toml`
# in the tree - at which point the suffix arm skips saying "no tracked .toml
# files" and is once again describing the enumeration rather than the tree.
#
# So completeness is anchored on four paths this repository cannot lose without
# a deliberate act, spanning the shapes the sweep cares about: a dotfile, a
# `.md`, a `.py` under a subdirectory, and an `.ini` at the root. Each was
# confirmed present in `git ls-files` on 2026-09-08. Renaming one of these is
# meant to redden this guard - that is the tripwire working, not a false alarm.
_ENUMERATION_ANCHORS = (".gitattributes", "CLAUDE.md", "core/types.py", "pytest.ini")


# ---------------------------------------------------------------------------
# EVERY GIT LAUNCH IS BOUNDED, AND NO LAUNCH FAILURE REACHES A READER AS A
# TRACEBACK
# ---------------------------------------------------------------------------

# A DEADLINE, and it has to be one. Measured 2026-09-08 with a `git ls-files`
# stalled at the subprocess layer, importing this module took 12247ms for a 12s
# stall and would have taken exactly as long as the stall lasted - no output, no
# diagnostic, and the whole `tests` suite waiting behind it. 20s is far above
# the sub-second real answer on this tree and far below the unbounded wait, so
# it can only fire on a tool that has stopped answering.
_GIT_TIMEOUT_SECONDS = 20.0


class _GitCall(typing.NamedTuple):
    """One git launch, with NO ANSWER AT ALL held apart from a non-zero exit.

    `failure` is None when git ran and said something, whatever it said. A
    caller that reads `returncode` without reading `failure` first is reading
    the -1 placeholder as a real exit code, which is why they travel together.
    """

    returncode: int
    stdout: str
    failure: str | None


def _launch_git(args: list[str]) -> _GitCall:
    """Run git under a deadline, and turn ANY launch failure into a string.

    THIS RUNS AT IMPORT, which is what makes both repairs load-bearing.
    `_measure_baseline()` must consult the real tools before any arm can install
    a stub, so it cannot be deferred - and anything that escapes it escapes
    during COLLECTION, where pytest has no test to attach it to.

    BOUNDED - see `_GIT_TIMEOUT_SECONDS` for the measurement.

    LEGIBLE. The catch this replaces was `except OSError`, and `subprocess.run`
    raises plenty that is not an OSError. Measured 2026-09-08 with a
    `ValueError` injected at the subprocess layer, `python -m pytest
    tests/test_line_endings.py` ended in a RAW TRACEBACK and `Interrupted: 1
    error during collection`, EXIT=2 - the entire file gone, which is the exact
    outcome `tests/conftest.py` exists to remove, and a raw error string in an
    operator surface besides.

    `Exception` and NOT `BaseException`, deliberately: a KeyboardInterrupt must
    still stop the run, and `pytest.skip`/`pytest.fail` raise BaseException
    subclasses that a stub is entitled to use. The `try` wraps the LAUNCH ONLY,
    so a defect in the classifier below still surfaces as itself rather than
    being laundered into "git could not be launched".
    """
    try:
        completed = subprocess.run(
            args,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return _GitCall(
            -1,
            "",
            f"`{' '.join(args)}` did not answer within {_GIT_TIMEOUT_SECONDS:g}s and was "
            "killed, so nothing here is entitled to a verdict about this tree",
        )
    except Exception as exc:  # noqa: BLE001 - none of it may reach collection
        return _GitCall(
            -1,
            "",
            f"`{' '.join(args)}` could not be launched: {type(exc).__name__}: {exc}",
        )
    return _GitCall(completed.returncode, completed.stdout, None)


def _classify_enumeration(returncode: int, stdout: str) -> _Enumeration:
    """The PURE half of the enumeration, so every failure branch is testable.

    Split out precisely because the alternative - proving these branches by
    breaking git - is a thing no test may do to a shared tree, and a branch
    nobody can reach is a branch nobody has checked.
    """
    if returncode != 0:
        return _Enumeration("FAILED", (), f"`git ls-files` exited {returncode}")
    files = tuple(line for line in stdout.splitlines() if line)
    if not files:
        return _Enumeration("FAILED", (), "`git ls-files` exited 0 but printed no paths")
    if len(files) < _MIN_TRACKED_FILES:
        return _Enumeration(
            "FAILED",
            (),
            f"`git ls-files` printed only {len(files)} paths, under the floor of "
            f"{_MIN_TRACKED_FILES}, so the enumeration is not the whole tree",
        )
    missing = [anchor for anchor in _ENUMERATION_ANCHORS if anchor not in files]
    if missing:
        return _Enumeration(
            "FAILED",
            (),
            f"`git ls-files` printed {len(files)} paths but not {missing}, so it "
            "enumerated some other corpus and not this repository",
        )
    return _Enumeration("OK", files, f"{len(files)} tracked paths")


def _tracked_enumeration() -> _Enumeration:
    """Ask git what the tree tracks, and never launder a failure into silence.

    `check=False`, deliberately. The version this replaces used `check=True`,
    which does fail loudly on a non-zero exit - measured, an injected exit 3
    reddened 9 arms - but says nothing at all about exit 0 with empty output,
    which is the hole. Classifying every outcome in one place is what makes the
    two cases answerable side by side.
    """
    # Asked HERE rather than at module level: the two arms below that read bytes
    # off disk - the .githooks/ shims and the CRLF detector itself - need no
    # repository and must keep running in a Download-ZIP copy.
    reason = git_unusable_reason()
    if reason is not None:
        return _Enumeration("UNAVAILABLE", (), reason)
    call = _launch_git(["git", "ls-files"])
    if call.failure is not None:
        return _Enumeration("FAILED", (), call.failure)
    return _classify_enumeration(call.returncode, call.stdout)


# ---------------------------------------------------------------------------
# THE GATE ASKS WHETHER GIT ENUMERATES THIS CORPUS - NOT WHETHER SOME
# REPOSITORY EXISTS SOMEWHERE ABOVE THIS DIRECTORY
# ---------------------------------------------------------------------------


def _repository_toplevel() -> Path | None:
    """The root of the repository git resolves from here, or None if it cannot.

    AN INDEPENDENT SIGNAL, and its independence is its entire job.
    test_the_corpus_gate_agrees_with_gits_own_topology grades the gate against
    this, and the gate is built on `git ls-files`. A gate graded by the
    predicate it consults is not graded at all - that is precisely how the
    previous version passed: it checked `git_unusable_reason()` against
    `git_unusable_reason()`.

    THE RESIDUAL IS STATED RATHER THAN HIDDEN: this and the gate are two
    different git subcommands answering two different questions, but they do
    share one `git` binary. A binary that lied consistently would satisfy both,
    and nothing in this file can see that.
    """
    call = _launch_git(["git", "rev-parse", "--show-toplevel"])
    if call.failure is not None or call.returncode != 0 or not call.stdout.strip():
        return None
    return Path(call.stdout.strip()).resolve()


class _Baseline(typing.NamedTuple):
    """What the UNMODIFIED tools say about this tree, measured once at import.

    `reason` is the gate: None when git enumerates THIS corpus, otherwise the
    text saying why it does not. `enumeration` is the classification of the
    same measurement, kept so the corpus helpers can serve the real paths
    without re-running a tool that a stub may since have replaced.
    """

    reason: str | None
    enumeration: _Enumeration


def _measure_baseline() -> _Baseline:
    """Ask the real tools ONCE, at import, before any stub can be installed.

    MEASURED AT IMPORT AND NOT LAZILY CACHED, deliberately. Nearly every arm
    below installs a `monkeypatch.setattr(subprocess, "run", ...)`, so a
    baseline computed on first use would be whatever the first stubbed arm
    happened to see, and the gate would then be a statement about a fixture.
    Import runs before collection, so what this consults is the real thing.

    ZERO PATHS IS THE ONE OUTCOME THAT MEANS "NOT THIS CORPUS", and it is held
    apart from every other failing classification on purpose:

      - exit 0, zero paths -> git works and tracks nothing at this path. That
        is a fact about the ENVIRONMENT, not a broken tool: a Download-ZIP,
        sdist or `git archive` copy, INCLUDING one extracted inside some other
        repository. Trackedness here is unknowable, so the guards SKIP.
      - exit 0, some paths, but under the floor or missing an anchor -> git
        tracks something here and the enumeration is not this repository. The
        gate stays CLOSED and `_tracked_files()` still FAILS loudly, because
        that is a real defect a reader can act on.
      - non-zero exit, or the tool would not launch -> same, loud.

    Widening the skip to every failing classification would have been the
    cheaper edit and the wrong one: it would retire the floor and the anchors
    in exactly the tree where they have something to say.
    """
    reason = git_unusable_reason()
    if reason is not None:
        # A DISK PROBE, because git's own 128 text is misleading in two real
        # worlds. Measured 2026-09-08: a FULL CLONE with a corrupt
        # `.git/config`, and separately one with a bogus `GIT_DIR` in the
        # environment, both reach this branch carrying git's wording "this tree
        # is not a git repository ... clone the repository to enforce this
        # guard" - false in a full clone, and it sends the reader somewhere
        # useless. Disk presence is independent of what git said, so it can
        # contradict it.
        shape = (
            "a `.git` entry IS present at this path, so this is a repository whose git "
            "directory could not be read rather than a copy with no repository at all - "
            "read any quoted advice to clone as git's own wording, not as a diagnosis"
            if (REPO_ROOT / ".git").exists()
            else "no `.git` entry is present at this path"
        )
        return _Baseline(
            f"git cannot answer for {REPO_ROOT}, so trackedness of this corpus is "
            f"unknowable and this guard is SKIPPED rather than passed. {shape}. "
            f"git reported: {reason}",
            _Enumeration("UNAVAILABLE", (), reason),
        )
    call = _launch_git(["git", "ls-files"])
    if call.failure is not None:
        return _Baseline(
            f"{call.failure}, so trackedness of this corpus is unknowable and this guard "
            "is SKIPPED rather than passed",
            _Enumeration("FAILED", (), call.failure),
        )
    enumeration = _classify_enumeration(call.returncode, call.stdout)
    if call.returncode == 0 and not [line for line in call.stdout.splitlines() if line]:
        return _Baseline(
            f"git runs here and tracks NOTHING at this path: `git ls-files` in "
            f"{REPO_ROOT} exited 0 and printed 0 paths, while the repository git "
            f"resolves to from here is rooted at {_repository_toplevel()}. Trackedness "
            "of THIS corpus is therefore unknowable and this guard is SKIPPED rather "
            "than passed. That is the normal state of a Download-ZIP, sdist or `git "
            "archive` copy - INCLUDING one extracted inside some other repository, "
            "where `git rev-parse --git-dir` succeeds by walking UP and says nothing "
            "whatever about this tree",
            enumeration,
        )
    return _Baseline(None, enumeration)


_BASELINE = _measure_baseline()


def _corpus_gate_reason() -> str | None:
    """None when git enumerates this corpus; otherwise why these guards SKIP.

    THE ONE SKIP PREDICATE IN THIS FILE. It was three - the injection gate, the
    corpus deriver and the tracked-file reader each opened a door of its own,
    and only one of them was ever graded. Measured 2026-09-08 against that
    version: forcing `_plausible_corpus()`'s skip to fire unconditionally left
    the file at 25 passed, 11 SKIPPED, EXIT=0, with all 11 skips at one line -
    a mutant that retired eleven arms and SURVIVED, while the file's own
    comment claimed thirteen of thirteen mutants died.

    Collapsing the three doors onto this one name is what makes them gradable
    together, and all three directions now have an arm:

      - forced open  -> test_forcing_the_corpus_gate_open_skips_every_consumer
      - forced shut  -> test_the_corpus_gate_agrees_with_gits_own_topology,
                        against `git rev-parse --show-toplevel`, which is NOT
                        the predicate the gate consults
      - a consumer skipping while this is shut ->
                        test_no_corpus_helper_skips_while_the_corpus_gate_is_closed

    A function rather than the constant itself, so an arm can monkeypatch it by
    name and every consumer moves together.
    """
    return _BASELINE.reason


def _tracked_files() -> list[str]:
    """The tracked paths - or a SKIP, or a FAILURE, and never a bare empty list.

    THE THREE OUTCOMES ARE KEPT DISTINCT, which is the whole repair:

      UNAVAILABLE -> skip, naming the missing repository. Trackedness is
                     genuinely unknowable in a Download-ZIP copy, and the suite
                     must stay usable there.
      FAILED      -> FAIL, naming the tool failure. git was there and did not
                     answer, so nothing below is entitled to a verdict.
      OK          -> the paths.

    The version this replaces returned `[]` for the middle case, and `[]` is
    what a tree holding no such file also looks like.

    THE GATE COMES FIRST, and that is the outer-repository repair. Where git
    enumerates nothing about this corpus the UNAVAILABLE disposition is the
    true one, and the version this replaces reached it only when
    `git rev-parse --git-dir` failed - which it does not inside another
    repository.
    """
    gate = _corpus_gate_reason()
    if gate is not None:
        pytest.skip(gate)
    enumeration = _tracked_enumeration()
    if enumeration.status == "UNAVAILABLE":
        pytest.skip(enumeration.reason)
    if enumeration.status != "OK":
        pytest.fail(
            f"the tracked-file enumeration did not run, so this guard checked NOTHING and "
            f"must not report a pass: {enumeration.reason}"
        )
    return list(enumeration.files)


def _files_declared_lf() -> list[str]:
    """Every tracked path whose `.gitattributes` rule resolves to `eol=lf`.

    Asked of git rather than reimplemented, so the answer cannot drift from the
    rules actually in force. `check-attr -z` is used because a filename may
    contain a colon, which the default output format also uses as a separator.
    """
    tracked = _tracked_files()

    completed = subprocess.run(
        ["git", "check-attr", "--stdin", "-z", "eol"],
        cwd=REPO_ROOT,
        # -z changes the INPUT separator as well as the output one. Feeding
        # newline-separated paths here makes git read the whole list as a
        # single path with embedded newlines, and the sweep silently collapses
        # to one bogus entry - which still passes a naive assertion.
        input="\0".join(tracked),
        capture_output=True,
        text=True,
        check=False,
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    # THE SAME ROOT CAUSE, ONE TOOL FURTHER DOWN. `check-attr` can fail the same
    # two ways `ls-files` can, and its empty answer wears the same clothes: zero
    # triples parsed reads as "no file declares eol=lf", which is what a tree
    # with no `.gitattributes` would also produce.
    if completed.returncode != 0:
        pytest.fail(
            f"`git check-attr` exited {completed.returncode} over {len(tracked)} tracked "
            "paths, so the eol=lf sweep has no corpus and must not report a pass"
        )
    # -z emits a flat NUL-separated stream of (path, attribute, value) triples
    # and TERMINATES every field, so the stream ends in one empty tail field.
    # Measured 2026-09-08: 195 tracked paths produced 586 fields, 3 * 195 + 1.
    fields = completed.stdout.split("\0")
    if fields and fields[-1] == "":
        fields = fields[:-1]
    # COUNTED AGAINST THE QUESTION ASKED, and this is the whole repair here. The
    # version this replaces asked only `len(fields) < 3`, which is a test for
    # TOTAL emptiness and blind to every SHORT answer between one triple and
    # N-1. Measured 2026-09-08 against that version: a `check-attr` answering a
    # single triple `data/x.png eol unspecified` reduced the sweep to zero files
    # and the CRLF guard passed over NOTHING, and a single `core/types.py eol
    # lf` reduced it to one file out of 195 and passed as well. Neither is
    # distinguishable from a fact about the tree, which is precisely the defect
    # this module exists to remove. A tool asked about N paths that answers
    # about fewer than N did not answer the question, so the count - not mere
    # non-emptiness - is what the sweep is entitled to reason from.
    if len(fields) % 3 or len(fields) // 3 != len(tracked):
        pytest.fail(
            f"`git check-attr` exited 0 but printed {len(fields)} NUL-separated fields "
            f"for {len(tracked)} tracked paths, where {3 * len(tracked)} were required "
            "- it answered about a different corpus than the one it was asked about, "
            "so the eol=lf sweep must not report a pass"
        )
    return [
        fields[i]
        for i in range(0, len(fields) - 2, 3)
        if fields[i + 1] == "eol" and fields[i + 2] == "lf"
    ]


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_no_file_declared_eol_lf_carries_crlf_in_the_working_tree():
    offenders = []
    for name in _files_declared_lf():
        path = REPO_ROOT / name
        if not path.is_file():
            continue  # A deleted-but-staged path is not this test's problem.
        count = path.read_bytes().count(CRLF)
        if count:
            offenders.append(f"{name} ({count} CRLF)")

    assert not offenders, (
        "these files declare eol=lf but carry CRLF on disk; the index hides "
        "this so no diff will show it: " + ", ".join(sorted(offenders))
    )


def _githook_files() -> list[Path]:
    """Every file under `.githooks/` that this working tree actually owns.

    RECURSIVE, where this used to be a one-level `iterdir()`. A shim that
    sources a helper out of `.githooks/lib/` would have carried the silent
    broken-shebang defect this guard exists to catch, and the old sweep could
    not see one directory down.

    EXCLUDED, because recursion is what makes a stray nested checkout reachable.
    `swept_files` drops dot-directories and any directory carrying a `.git`
    entry; note that `.githooks` is itself a dot-directory and is the sweep
    ROOT, which the predicate never applies to itself - see its docstring.
    """
    return swept_files(REPO_ROOT / ".githooks")


def test_the_githooks_shims_are_lf_because_a_crlf_shebang_breaks_them():
    """Called out separately because the failure here is a SILENT missing gate.

    A CRLF shebang makes the kernel look for an interpreter literally named
    "/bin/sh\\r". The hook then fails with an unreadable error or is skipped,
    and a gate that is absent without saying so is the whole thing this
    scaffold exists to prevent.
    """
    checked = _githook_files()
    assert checked, ".githooks/ swept to nothing - zero out of zero is not a pass"
    for shim in checked:
        rel = shim.relative_to(REPO_ROOT).as_posix()
        assert CRLF not in shim.read_bytes(), f"{rel} has CRLF"


# ---------------------------------------------------------------------------
# Non-vacuity - a sweep that stopped finding files would pass forever
# ---------------------------------------------------------------------------


def test_the_sweep_selects_a_realistic_number_of_files():
    """The floor is `_MIN_TRACKED_FILES`, not a second bare literal beside it.

    This used to read `>= 50`. Two independent copies of the same number are
    two things to drift apart, and the mutant proves it was slack rather than a
    check: measured 2026-09-08, raising that bare 50 to 190 left this file at
    31 passed, EXIT=0, because the tree declares more than 190. Naming the
    constant leaves ONE literal to grade, and
    test_the_floor_keeps_wide_clearance_below_the_real_tree grades it.
    """
    declared = _files_declared_lf()
    assert len(declared) >= _MIN_TRACKED_FILES, (
        f"only {len(declared)} files resolved to eol=lf"
    )
    assert "core/types.py" in declared
    assert "CLAUDE.md" in declared


def test_the_sweep_excludes_files_declared_binary():
    """`.gitattributes` marks images and archives binary; they must not appear."""
    declared = set(_files_declared_lf())
    assert not [name for name in declared if name.endswith((".png", ".jpg", ".ico", ".zip"))]


def test_a_crlf_byte_would_actually_be_detected(tmp_path):
    """Aimed at the detection itself, not at the file list."""
    clean = tmp_path / "clean.txt"
    dirty = tmp_path / "dirty.txt"
    clean.write_bytes(b"one\ntwo\n")
    dirty.write_bytes(b"one\r\ntwo\n")
    assert clean.read_bytes().count(CRLF) == 0
    assert dirty.read_bytes().count(CRLF) == 1


@pytest.mark.parametrize("suffix", [".py", ".md", ".json", ".yml", ".toml", ".ini"])
def test_every_source_suffix_the_tree_uses_is_covered_by_the_sweep(suffix: str):
    """A suffix that stopped resolving to eol=lf would silently leave the guard."""
    declared = _files_declared_lf()
    tracked_with_suffix = [name for name in _tracked_files() if name.endswith(suffix)]
    if not tracked_with_suffix:
        pytest.skip(f"no tracked {suffix} files")
    assert any(name.endswith(suffix) for name in declared), f"{suffix} is not covered"


# ---------------------------------------------------------------------------
# THE ENUMERATION MUST NOT REPORT "COULD NOT CHECK" AS "CHECKED AND FOUND NONE"
# ---------------------------------------------------------------------------


def _stub_ls_files(returncode: int, stdout: str):
    """A subprocess.run that breaks ONLY `git ls-files`, honouring `check`."""
    real = subprocess.run

    def fake(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and list(cmd[:2]) == ["git", "ls-files"]:
            if kwargs.get("check") and returncode != 0:
                raise subprocess.CalledProcessError(returncode, cmd, output=stdout, stderr="")
            return subprocess.CompletedProcess(cmd, returncode, stdout, "")
        return real(cmd, *args, **kwargs)

    return fake


@pytest.mark.parametrize("returncode,stdout", [(0, ""), (3, ""), (0, "\n\n")])
def test_a_broken_enumeration_fails_the_suffix_arm_rather_than_skipping_it(
    monkeypatch, returncode: int, stdout: str
):
    """GRADES THE CALLER, not a predicate - the five recurrences here were all
    a gate proven pure and never proven wired.

    Measured 2026-09-08 before the repair: with `git ls-files` exiting 0 and
    printing nothing, this arm raised Skipped carrying the text "no tracked .py
    files" against a tree holding 113 tracked `.py` files. A skip is how a
    guard says "nothing to see", so the coverage claim retired while reading
    green.
    """
    _require_a_repository_to_break()
    monkeypatch.setattr(subprocess, "run", _stub_ls_files(returncode, stdout))
    # BaseException and not Exception, and the difference is measured. pytest's
    # Skipped derives from BaseException, so `pytest.raises(Exception)` lets the
    # skip fly straight past and the ARM ITSELF reports as skipped - a guard
    # against silent skipping that silently skips. Observed 2026-09-08: two of
    # these three parametrisations reported `s` rather than red.
    with pytest.raises(BaseException) as caught:
        test_every_source_suffix_the_tree_uses_is_covered_by_the_sweep(".py")
    assert not isinstance(caught.value, _SKIPPED), (
        "a failed enumeration was reported as a SKIP, which is indistinguishable "
        f"from a tree that genuinely holds no .py files: {caught.value}"
    )


def test_a_broken_enumeration_fails_the_crlf_sweep_rather_than_passing_it(monkeypatch):
    """The sweep itself, and the worse half of the same root cause.

    An empty file list makes the CRLF loop iterate zero times and the assertion
    hold trivially. Measured before the repair: this arm PASSED under an
    enumeration that returned nothing at all.
    """
    _require_a_repository_to_break()
    monkeypatch.setattr(subprocess, "run", _stub_ls_files(0, ""))
    # BaseException and not Exception, and the difference is measured. pytest's
    # Skipped derives from BaseException, so `pytest.raises(Exception)` lets the
    # skip fly straight past and the ARM ITSELF reports as skipped - a guard
    # against silent skipping that silently skips. Observed 2026-09-08: two of
    # these three parametrisations reported `s` rather than red.
    with pytest.raises(BaseException) as caught:
        test_no_file_declared_eol_lf_carries_crlf_in_the_working_tree()
    assert not isinstance(caught.value, _SKIPPED), (
        f"a failed enumeration let the CRLF sweep report a pass over zero files: {caught.value}"
    )


def _plausible_corpus(drop_suffix: str = "") -> str:
    """This repository's real `git ls-files` output, optionally minus a suffix.

    DERIVED FROM THE REAL TREE rather than hand-typed, because a hand-typed
    corpus can only prove the classifier agrees with the person who typed it.
    The one thing it is allowed to differ in is the suffix under test.

    THAT DERIVATION IS ITSELF A GIT DEPENDENCY, and it is disposition 3 above.
    `check=True` here raised `CalledProcessError` in the no-git copy - six of
    the sixteen failures measured 2026-09-08 were this call, not an assertion -
    which is a crash rather than a verdict. There is no real corpus to derive
    without a repository, so the arms that need one skip, saying which.

    SERVED FROM THE IMPORT-TIME BASELINE, and it no longer runs git at all.
    Two things follow, both wanted. It cannot be answered by a stub some arm
    installed - a corpus deriver that read a fixture would be grading the
    fixture. And its skip is now the ONE gate rather than a second door of its
    own: the unconditional-skip mutant that survived here, retiring 11 arms at
    EXIT=0, dies against
    test_no_corpus_helper_skips_while_the_corpus_gate_is_closed.

    THE FAIL BRANCH IS NOT THE SKIP BRANCH. Where git DOES enumerate this
    corpus but the enumeration is unusable - short of the floor, missing an
    anchor - there is still no real corpus to derive, and that is a defect
    rather than an environment, so it is loud.
    """
    gate = _corpus_gate_reason()
    if gate is not None:
        pytest.skip(
            "this arm needs THIS tree's real `git ls-files` output as its corpus, "
            "and a hand-typed substitute would only prove the classifier agrees "
            f"with whoever typed it: {gate}"
        )
    if _BASELINE.enumeration.status != "OK":
        pytest.fail(
            "git enumerates this corpus but its answer is not usable, so there is no "
            "real corpus to derive and this arm must not report a pass: "
            f"{_BASELINE.enumeration.reason}"
        )
    lines = list(_BASELINE.enumeration.files)
    if drop_suffix:
        lines = [line for line in lines if not line.endswith(drop_suffix)]
    return "\n".join(lines) + "\n"


def test_the_classifier_calls_every_way_the_enumeration_can_break_a_failure():
    """The pure half, driven through each failure mode - none may read as empty.

    A CONTROL THAT ONLY PLANTS THE CASE THE MATCHER HANDLES CANNOT DISCOVER
    THAT THE MATCHER IS NARROW, so these vary in shape rather than in degree:
    a non-zero exit, a silent success, whitespace that splits into nothing, a
    short list that clears none of the floor, and a long plausible list that
    clears the floor while being some other corpus entirely.
    """
    broken = {
        "a non-zero exit": _classify_enumeration(3, ""),
        "a non-zero exit that still printed paths": _classify_enumeration(128, "core/types.py\n"),
        "exit 0 with no output at all": _classify_enumeration(0, ""),
        "exit 0 with only blank lines": _classify_enumeration(0, "\n\n\n"),
        "exit 0 with a handful of paths": _classify_enumeration(0, "a.py\nb.py\nc.py\n"),
        "exit 0 with a large corpus that is not this tree": _classify_enumeration(
            0, "\n".join(f"vendor/mod_{i}.py" for i in range(400))
        ),
    }
    for shape, result in broken.items():
        assert result.status == "FAILED", f"{shape} was not classified as a failure: {result}"
        assert result.files == (), f"{shape} yielded files despite failing: {result}"
        assert result.reason, f"{shape} failed without naming a reason"


def test_positive_control_the_real_enumeration_classifies_as_ok():
    """Without this the arm above is satisfied by a classifier that always fails."""
    result = _classify_enumeration(0, _plausible_corpus())
    assert result.status == "OK", result.reason
    assert len(result.files) >= _MIN_TRACKED_FILES
    for anchor in _ENUMERATION_ANCHORS:
        assert anchor in result.files


def test_the_floor_is_not_decorative_and_can_actually_fail():
    """A FLOOR THAT NOTHING CAN TRIP PASSES FOREVER AND CHECKS NOTHING.

    Proven by construction, from the real corpus rather than an invented one:
    truncated to one path under the floor it must FAIL, and to exactly the
    floor it must not fail FOR THAT REASON. So the set of inputs where the
    floor fires is demonstrably non-empty, and its edge sits where the literal
    says it does.
    """
    corpus = [line for line in _plausible_corpus().splitlines() if line]
    assert len(corpus) > _MIN_TRACKED_FILES, (
        "this tree no longer has enough tracked files to demonstrate the floor, so the "
        "floor is no longer known to be reachable and must be re-derived"
    )

    under = _classify_enumeration(0, "\n".join(corpus[: _MIN_TRACKED_FILES - 1]) + "\n")
    assert under.status == "FAILED"
    assert "floor" in under.reason, under.reason

    # One more path, and the floor specifically has nothing left to say. The
    # anchors may or may not be in this slice, so this asserts on the REASON
    # and not on the status - a shape arm pins format, not value, and claiming
    # OK here would be pinning something this input does not establish.
    at_floor = _classify_enumeration(0, "\n".join(corpus[:_MIN_TRACKED_FILES]) + "\n")
    assert "floor" not in at_floor.reason, at_floor.reason


def test_the_floor_keeps_wide_clearance_below_the_real_tree():
    """THE ARM ABOVE PINS THE FLOOR'S EDGE; THIS ONE PINS WHERE THE EDGE SITS.

    Measured 2026-09-08, `_MIN_TRACKED_FILES` raised from 50 to 150 - and to
    190 - left this file at 31 passed, EXIT=0. Every existing arm was written
    RELATIVE to the constant, so all of them moved with it and about 140 of
    undetected slack sat between those two values. A constant nothing can
    disagree with is not a measurement.

    What the floor is FOR is the claim it must satisfy: it separates a broken
    enumeration - which returns nothing, or a handful - from any plausible
    state of this repository. That requires clearance on both sides, so it is
    asserted on both sides:

      - at most half the real corpus, so ordinary shrinkage, a large deletion
        or a split cannot make the floor fire on a healthy tree. 150 and 190
        both violate this against the 195 paths measured 2026-09-08;
      - at least 10, so it cannot be lowered to a value a hung `ls-files`
        printing two lines would clear.

    Deliberately NOT an equality against 50. Pinning the literal to itself
    would be a tautology that reddens on any legitimate re-derivation, which is
    a worse guard than none. The interval is the claim.
    """
    corpus = [line for line in _plausible_corpus().splitlines() if line]
    assert _MIN_TRACKED_FILES * 2 <= len(corpus), (
        f"the floor of {_MIN_TRACKED_FILES} is more than half the {len(corpus)} paths this "
        "tree tracks, so it has stopped being a broken-enumeration detector and become an "
        "assertion about the tree's size, which will fire on a legitimate shrinkage"
    )
    assert _MIN_TRACKED_FILES >= 10, (
        f"a floor of {_MIN_TRACKED_FILES} is low enough for a badly broken enumeration to "
        "clear it, so it would no longer separate the cases it exists to separate"
    )


def test_the_anchor_check_catches_a_partial_enumeration_the_floor_cannot():
    """The floor and the anchors catch DIFFERENT partials, so both must exist.

    This input clears the floor comfortably - it is the whole tree bar one
    file - and is still not an enumeration anybody may reason from.
    """
    corpus = [line for line in _plausible_corpus().splitlines() if line and line != "CLAUDE.md"]
    assert len(corpus) > _MIN_TRACKED_FILES, "the corpus must clear the floor for this arm to mean anything"
    result = _classify_enumeration(0, "\n".join(corpus) + "\n")
    assert result.status == "FAILED", "a corpus missing an anchor cleared both checks"
    assert "CLAUDE.md" in result.reason


def test_a_missing_repository_is_a_skip_and_a_broken_git_is_not(monkeypatch):
    """The one case where skipping IS the honest answer must keep working.

    UNAVAILABLE and FAILED are the two halves this repair separates, and an
    arm that only proved FAILED would leave the suite unusable in the
    Download-ZIP copy `tests/conftest.py` exists to serve.
    """
    monkeypatch.setattr(
        "tests.test_line_endings.git_unusable_reason", lambda: "this tree is not a git repository"
    )
    unavailable = _tracked_enumeration()
    assert unavailable.status == "UNAVAILABLE"
    with pytest.raises(_SKIPPED):
        _tracked_files()


def test_a_true_ran_and_found_nothing_still_skips_rather_than_failing(monkeypatch):
    """THE SWEEP MUST NOT SCORE BY DELETING ITS LEGITIMATE NEIGHBOURS.

    A complete enumeration that genuinely holds no file of some suffix is a
    real ran-and-found-nothing, and skipping is the correct answer for it. This
    plants exactly that: the whole tree with every `.toml` removed - it clears
    the floor, carries all four anchors, and is missing a suffix. `.toml` is
    chosen because no anchor carries that suffix, so the arm turns on the
    absence and not on a broken corpus.
    """
    monkeypatch.setattr(subprocess, "run", _stub_ls_files(0, _plausible_corpus(".toml")))
    with pytest.raises(_SKIPPED) as caught:
        test_every_source_suffix_the_tree_uses_is_covered_by_the_sweep(".toml")
    assert "no tracked .toml files" in str(caught.value)


def test_positive_control_the_same_corpus_intact_does_not_skip_that_suffix(monkeypatch):
    """ONE thing differs from the arm above: the `.toml` paths are still there.

    Without this, an implementation that skipped every suffix unconditionally
    would satisfy the arm above and check nothing.
    """
    monkeypatch.setattr(subprocess, "run", _stub_ls_files(0, _plausible_corpus()))
    test_every_source_suffix_the_tree_uses_is_covered_by_the_sweep(".toml")


# ---------------------------------------------------------------------------
# THE SAME HOLE ONE TOOL FURTHER DOWN - `git check-attr`
#
# `_tracked_files()` above is now graded by seven arms. `_files_declared_lf()`,
# which consumes it, was not graded by any: measured 2026-09-08, replacing BOTH
# of its `pytest.fail` branches with `if False:` left this file at 22 passed,
# EXIT=0, while the same mutation applied to the floor or the anchors reddened
# it. An unreachable branch is not a guard, it is a comment that costs a line
# number. These arms exist so that a mutant of either branch dies.
#
# AND THE COUNT BRANCH IS TWO CLAUSES, NOT ONE. `len(fields) % 3` and
# `len(fields) // 3 != len(tracked)` fail on different streams, so each needs
# an input of its own or the file grades a guard it does not have: measured
# 2026-09-08, dropping the modulo clause and weakening `!=` to `<` each left
# this file green. The dangling-field arm and the over-answer arm below are
# those two inputs.
# ---------------------------------------------------------------------------


def _stub_check_attr(returncode: int, stdout: str):
    """A subprocess.run that breaks ONLY `git check-attr`.

    Mirrors `_stub_ls_files` deliberately, and the passthrough is the reason:
    `_files_declared_lf()` calls `git ls-files` first, and an arm that broke
    both tools at once would be answered by the ls-files guards and prove
    nothing whatever about the check-attr ones.

    THE `check` BRANCH IS PART OF THE MIRROR, and it was missing. This stub
    used to return a `CompletedProcess` carrying a non-zero returncode even
    when the caller passed `check=True`, where the real `subprocess.run`
    raises `CalledProcessError`. `_real_check_attr_answer()` is the one caller
    in this file that passes `check=True`, and every arm evaluates it BEFORE
    the `monkeypatch.setattr` lands, so the divergence was latent rather than
    live. It is fixed rather than documented because a harness distinguishable
    from production grades the wrong thing, and a docstring claiming a mirror
    that is not one is worse than no docstring at all.
    test_the_two_stubs_honour_check_identically grades the claim.
    """
    real = subprocess.run

    def fake(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and list(cmd[:2]) == ["git", "check-attr"]:
            if kwargs.get("check") and returncode != 0:
                raise subprocess.CalledProcessError(returncode, cmd, output=stdout, stderr="")
            return subprocess.CompletedProcess(cmd, returncode, stdout, "")
        return real(cmd, *args, **kwargs)

    return fake


def _real_check_attr_answer() -> str:
    """This tree's genuine `check-attr` stream, for the positive control.

    Derived rather than typed, for the reason `_plausible_corpus` gives: a
    hand-written stream can only prove the parser agrees with its author, and
    the field count is exactly the thing under test here.
    """
    tracked = [line for line in _plausible_corpus().splitlines() if line]
    return subprocess.run(
        ["git", "check-attr", "--stdin", "-z", "eol"],
        cwd=REPO_ROOT,
        input="\0".join(tracked),
        capture_output=True,
        text=True,
        check=True,
        timeout=_GIT_TIMEOUT_SECONDS,
    ).stdout


def _short_answer(triples: int) -> str:
    """A well-formed `check-attr` stream that is simply too SHORT.

    Every field is real and the record shape is exactly right - which is the
    point. The defect this catches is not malformed output, it is a truthful
    answer about the wrong number of files.
    """
    fields = _real_check_attr_answer().split("\0")
    if fields and fields[-1] == "":
        fields = fields[:-1]
    return "\0".join(fields[: triples * 3]) + "\0"


def _real_check_attr_fields() -> list[str]:
    """This tree's real `check-attr` stream, trailing empty field removed.

    The same two lines `_files_declared_lf()` runs, so the two agree on what
    "the fields" means and the arms below can do arithmetic on the result.
    """
    fields = _real_check_attr_answer().split("\0")
    if fields and fields[-1] == "":
        fields = fields[:-1]
    return fields


def _answer_with_one_dangling_field() -> str:
    """A COMPLETE answer, plus the first field of a truncated next record.

    THE ONE INPUT THE MODULO CLAUSE ALONE CAN CATCH. `check-attr` writing 195
    whole records and then dying part-way through a 196th - a broken pipe, a
    full disk, a kill between two of the three writes - leaves 585 real fields
    plus one dangling path. 586 % 3 is 1, so the record shape is wrong; but
    586 // 3 is 195, which is exactly `len(tracked)`, so the COUNT clause is
    satisfied and says nothing. This is not a contrived shape - a truncated
    write is the ordinary way a stream ends early.
    """
    return "\0".join([*_real_check_attr_fields(), "core/types.py"]) + "\0"


def _answer_with_one_extra_record() -> str:
    """A complete answer plus one whole extra record - a SYNTHETIC over-answer.

    SAID PLAINLY: no real `git check-attr --stdin` produces this. It emits one
    record per path it was given, so the over-answer side of `!=` cannot be
    reached by breaking the real tool, and an adversary who tried could not
    make it happen. The input is constructed.

    It is graded anyway because the guard is written as `!=`, and `!=` is a
    two-sided claim. Measured 2026-09-08 with only the short-answer arms
    planted, weakening it to `<` left this file at 31 passed, EXIT=0 - so half
    of the comparison under test had no input at all, and half a guard reads
    exactly like a whole one. A stream longer than the question is also an
    answer about a different corpus, whatever produced it.
    """
    return "\0".join([*_real_check_attr_fields(), "vendor/extra.py", "eol", "lf"]) + "\0"


@pytest.mark.parametrize(
    "shape,returncode,stdout",
    [
        # The branch that was unreachable, case one: the tool refused.
        ("a non-zero exit", 3, ""),
        ("a non-zero exit that still printed a triple", 1, "core/types.py\0eol\0lf\0"),
        # The branch that was unreachable, case two - and it was ALSO too
        # narrow. `len(fields) < 3` catches only the first of these three.
        ("exit 0 with no output at all", 0, ""),
        ("exit 0 with a single unspecified triple", 0, "data/x.png\0eol\0unspecified\0"),
        ("exit 0 with a single lf triple", 0, "core/types.py\0eol\0lf\0"),
        ("exit 0 with a ragged half-record", 0, "core/types.py\0eol\0"),
    ],
)
def test_a_broken_check_attr_fails_the_sweep_rather_than_emptying_it(
    monkeypatch, shape: str, returncode: int, stdout: str
):
    """GRADES THE CALLER. Every shape here left the sweep GREEN before today.

    Measured 2026-09-08 against the version this replaces: the single-triple
    `data/x.png eol unspecified` stream made `_files_declared_lf()` return `[]`
    and `test_no_file_declared_eol_lf_carries_crlf_in_the_working_tree` pass
    over ZERO files, and the single `core/types.py eol lf` stream made it pass
    over one file out of 195. Both read as facts about the tree.
    """
    _require_a_repository_to_break()
    monkeypatch.setattr(subprocess, "run", _stub_check_attr(returncode, stdout))
    # BaseException and not Exception, for the reason the ls-files arms give:
    # pytest's Skipped derives from BaseException, so `pytest.raises(Exception)`
    # would let a skip fly past and this arm would report `s` rather than red.
    with pytest.raises(BaseException) as caught:
        test_no_file_declared_eol_lf_carries_crlf_in_the_working_tree()
    assert not isinstance(caught.value, _SKIPPED), (
        f"{shape} was reported as a SKIP rather than a failure: {caught.value}"
    )
    assert isinstance(caught.value, _FAILED), (
        f"{shape} did not fail the sweep; it raised {type(caught.value).__name__}: {caught.value}"
    )


def test_a_non_zero_check_attr_exit_fails_even_when_the_answer_looks_complete(monkeypatch):
    """THE ONE INPUT THE EXIT-CODE BRANCH ALONE CAN CATCH, and it took a mutant
    to find that the branch had no such input.

    Measured 2026-09-08: with only the six shapes in the arm above planted,
    replacing `if completed.returncode != 0:` with `if False:` left this file
    at 30 passed, EXIT=0 - every one of those shapes is ALSO short, so the
    count check answered them all and the exit-code branch was doing no work
    that anything could observe. A guard no mutant kills has not been graded.

    So this plants a stream that is complete and well-formed and arrives with a
    non-zero exit, which is the shape a `check-attr` that answered and then
    failed on cleanup would produce. The count check is satisfied by it; only
    the exit code says the tool did not succeed.
    """
    _require_a_repository_to_break()
    monkeypatch.setattr(subprocess, "run", _stub_check_attr(7, _real_check_attr_answer()))
    with pytest.raises(_FAILED) as caught:
        _files_declared_lf()
    assert "exited 7" in str(caught.value), caught.value


def test_a_short_check_attr_answer_fails_even_though_it_clears_every_old_check(monkeypatch):
    """THE FLOOR'S SIBLING, and the exact hole the old `len(fields) < 3` left.

    This stream is well-formed, exits 0, and carries 60 real triples - more
    than `_MIN_TRACKED_FILES`, so no plausible non-emptiness or size heuristic
    catches it. It is still an answer about 60 of 195 files. Only counting it
    against the question asked sees this.
    """
    _require_a_repository_to_break()
    tracked = _tracked_files()
    assert len(tracked) > 60, "this tree is too small to demonstrate a short answer"
    monkeypatch.setattr(subprocess, "run", _stub_check_attr(0, _short_answer(60)))
    with pytest.raises(_FAILED) as caught:
        _files_declared_lf()
    assert "180" in str(caught.value), caught.value
    assert str(len(tracked)) in str(caught.value), caught.value


def test_a_dangling_field_after_a_complete_answer_is_caught_only_by_the_modulo(monkeypatch):
    """THE RAGGED-RECORD CLAUSE HAD NO INPUT OF ITS OWN, and a mutant found it.

    Measured 2026-09-08: reducing
    `if len(fields) % 3 or len(fields) // 3 != len(tracked):` to
    `if len(fields) // 3 != len(tracked):` left this file at 31 passed,
    EXIT=0. The "ragged half-record" shape already planted here - two fields
    total - is answered by the COUNT clause, since 0 // 3 is not 195, so it
    never exercised the modulo at all. The comment above these arms says they
    exist so that a mutant of either branch dies; this one did not.

    So this plants the input only the modulo can see, and asserts that
    arithmetic in the arm rather than trusting it: the field count leaves a
    remainder of 1, and the floor division equals `len(tracked)` exactly, so
    the count clause is satisfied and the modulo is the only thing left
    standing between the stream and a green sweep.
    """
    _require_a_repository_to_break()
    tracked = _tracked_files()
    stream = _answer_with_one_dangling_field()
    fields = stream.split("\0")[:-1]
    assert len(fields) % 3 == 1, (
        f"this arm needs a stream whose field count is NOT a multiple of 3; got {len(fields)}"
    )
    assert len(fields) // 3 == len(tracked), (
        "this arm needs a stream the COUNT clause accepts, otherwise it grades the count "
        f"and not the modulo: {len(fields)} // 3 is {len(fields) // 3}, tracked {len(tracked)}"
    )

    monkeypatch.setattr(subprocess, "run", _stub_check_attr(0, stream))
    with pytest.raises(_FAILED) as caught:
        _files_declared_lf()
    assert str(len(fields)) in str(caught.value), caught.value


def test_an_over_long_check_attr_answer_fails_although_no_real_git_makes_one(monkeypatch):
    """THE OTHER SIDE OF `!=`, and it is SYNTHETIC - stated because it is.

    `git check-attr --stdin` answers once per path it was given, so nothing an
    adversary can do to the real tool makes it over-answer. The input below is
    built by hand: the tree's own stream with one extra whole record appended.

    Grading it anyway is not decoration. Measured 2026-09-08, weakening the
    guard from `!= len(tracked)` to `< len(tracked)` left this file at 31
    passed, EXIT=0. A comparison with an input on only one side is a
    comparison nobody has checked, and the reason to reject a longer stream is
    the same as the reason to reject a shorter one: the tool answered about a
    corpus that is not the one it was asked about, and the sweep is not
    entitled to reason from it. Where that could come from - a stale stub, a
    wrapper script, a future `check-attr` that reports more than one attribute
    per path - is exactly the situation a guard should survive.
    """
    _require_a_repository_to_break()
    tracked = _tracked_files()
    stream = _answer_with_one_extra_record()
    fields = stream.split("\0")[:-1]
    assert len(fields) % 3 == 0, "the over-answer must be well formed, or it grades the modulo"
    assert len(fields) // 3 > len(tracked), (
        f"this arm needs MORE records than paths asked about: {len(fields) // 3} vs {len(tracked)}"
    )

    monkeypatch.setattr(subprocess, "run", _stub_check_attr(0, stream))
    with pytest.raises(_FAILED) as caught:
        _files_declared_lf()
    assert str(len(fields)) in str(caught.value), caught.value


def test_the_two_stubs_honour_check_identically(monkeypatch):
    """THE HARNESS MUST NOT BE DISTINGUISHABLE FROM PRODUCTION.

    `_stub_check_attr`'s docstring claims it mirrors `_stub_ls_files`. It did
    not: it returned a `CompletedProcess` carrying a non-zero returncode where
    the real `subprocess.run(check=True)` raises `CalledProcessError`. Latent,
    because every arm evaluates `_real_check_attr_answer()` before the
    `setattr` lands - but a latent divergence is a live one the moment somebody
    reorders two lines, and a docstring that describes a mirror is a claim.

    Graded from the outside, on both stubs and in both directions, because a
    mirror asserted about one half proves nothing about the pair.
    """
    for name, stub, cmd in (
        ("ls-files", _stub_ls_files, ["git", "ls-files"]),
        ("check-attr", _stub_check_attr, ["git", "check-attr", "--stdin", "-z", "eol"]),
    ):
        with pytest.raises(subprocess.CalledProcessError) as caught:
            stub(3, "")(cmd, capture_output=True, text=True, check=True)
        assert caught.value.returncode == 3, f"{name} stub raised the wrong returncode"

        # check=True with a ZERO exit must still return, or the stub would
        # break the positive controls instead of the negative ones.
        ok = stub(0, "x\n")(cmd, capture_output=True, text=True, check=True)
        assert ok.returncode == 0 and ok.stdout == "x\n", f"{name} stub broke a clean call"

        # check absent - the shape every failure arm here actually uses - must
        # hand back the non-zero code rather than raising.
        quiet = stub(3, "")(cmd, capture_output=True, text=True, check=False)
        assert quiet.returncode == 3, f"{name} stub raised where the caller did not ask it to"


def _corpus_gate_consumers() -> tuple[tuple[str, typing.Callable[[], object]], ...]:
    """Every helper in this file whose skip is the corpus gate.

    ENUMERATED IN ONE PLACE so the two arms below cannot grade different
    subsets of it. A door left off this tuple is a door nothing grades, which
    is the exact defect that let the `_plausible_corpus` mutant survive.
    """
    return (
        ("_require_a_repository_to_break", _require_a_repository_to_break),
        ("_tracked_files", _tracked_files),
        ("_plausible_corpus", _plausible_corpus),
    )


def test_the_corpus_gate_is_a_pure_read_of_the_one_import_time_measurement(monkeypatch):
    """THE GATE MAY NOT RE-CONSULT GIT, AND THAT IS CHECKABLE WITHOUT AN ORACLE.

    THE CEILING THIS ARM EXISTS TO RESPECT. The gate's proposition is "`git
    ls-files` enumerates THIS corpus", and the only instrument that can observe
    that proposition is `git ls-files`. Every other git subcommand answers a
    NEIGHBOURING proposition - topology, the HEAD tree, ignore rules - which is
    entitled to disagree, and grading a verdict against a neighbour manufactures
    a false red on a legitimate machine. That has now happened four times, most
    recently to the arm this one replaces: it graded the gate with a
    BICONDITIONAL against `git rev-parse --show-toplevel == REPO_ROOT`, and that
    biconditional is FALSE for a tree VENDORED INTO another repository AND
    TRACKED BY IT. Measured 2026-09-08 in exactly that world: toplevel was the
    OUTER root, `git ls-files` returned 184 paths OF THIS TREE with all four
    anchors present, the gate was correctly SHUT, every git-dependent guard ran
    and every one was right - and the file reported 1 failed, 37 passed, EXIT=1,
    asserting the falsehood that git had said nothing about this corpus.

    So this arm stops grading the VERDICT and grades the DERIVATION, which needs
    no second instrument:

      - the gate LAUNCHES NOTHING. It is a read of the one measurement taken at
        import. Any re-consultation - of `--show-toplevel` most of all - is
        visible as a subprocess launch, whether it goes through
        `_repository_toplevel()` or straight to `subprocess.run`.
      - the gate MOVES WITH that measurement, in both directions. A gate pinned
        open or pinned shut stops tracking it and dies here, in EVERY world
        rather than only in a checkout.

    WHAT THIS DOES NOT GUARANTEE, stated rather than hidden: nothing here says
    the measurement itself was RIGHT. A `git ls-files` that lied consistently -
    printing this tree's anchored paths inside a Download-ZIP copy, or nothing
    at all inside a real checkout - satisfies every arm in this file. There is
    no second instrument for that proposition, so it is a residual and not a
    gap somebody forgot to close.
    """
    launched: list[object] = []

    def recording(cmd, *args, **kwargs):
        launched.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, f"{REPO_ROOT}\n", "")

    monkeypatch.setattr(subprocess, "run", recording)

    # NON-VACUITY FIRST. "The recorder saw no launch" is worth nothing until the
    # recorder has been seen to record, and `_repository_toplevel()` exists to
    # make exactly the launch the gate must not make.
    control = _repository_toplevel()
    assert launched, (
        "the recorder observed no subprocess launch from _repository_toplevel(), whose "
        "entire body is one launch, so it cannot testify about the gate either - it "
        f"returned {control}"
    )

    for label, baseline in (
        (
            "OPEN",
            _Baseline(
                "forced: the import-time measurement says git does not enumerate this corpus",
                _Enumeration("UNAVAILABLE", (), "forced"),
            ),
        ),
        ("SHUT", _Baseline(None, _BASELINE.enumeration)),
    ):
        monkeypatch.setattr("tests.test_line_endings._BASELINE", baseline)
        launched.clear()
        observed = _corpus_gate_reason()
        assert not launched, (
            f"with the baseline forced {label} the corpus gate launched {launched}, so it "
            "consults a second route rather than reading the one import-time measurement. "
            "A gate that re-asks git is a gate graded by a signal that is entitled to "
            "disagree with it, which is how this file has produced a false red four times"
        )
        assert observed == baseline.reason, (
            f"with the baseline forced {label} the corpus gate answered {observed!r} "
            f"instead of {baseline.reason!r}, so it is not derived from the measurement "
            "at all and every arm that depends on it is running on a constant"
        )


def test_git_topology_grades_only_the_direction_it_can_actually_settle():
    """THE ONE IMPLICATION `--show-toplevel` SUPPORTS, AND NOT THE CONVERSE.

    Two directions are sound and are asserted; the third is not available from
    any single route and is SKIPPED with its reason rather than passed silently.

      - git resolves NO repository from here -> the gate MUST be OPEN. Sound
        without qualification: an enumeration of this corpus requires a
        repository to enumerate it. Live in the `rm -rf .git` and corrupt-config
        worlds.
      - the gate is SHUT -> the toplevel git resolves MUST be this directory or
        an ANCESTOR of it. Sound because `git ls-files` run at this path can only
        print this corpus while this path lies inside git's work tree, so a
        toplevel somewhere off to the side contradicts the gate. This is the
        branch that runs in an ordinary checkout AND in the vendored-and-tracked
        world, and it is an ancestor test and not an equality test precisely
        because the vendored world is legitimate.
      - the gate is OPEN while git does resolve some repository -> NOTHING here
        can settle it. That is a tree inside a repository that does not track it
        - a Download-ZIP or `git archive` extract dropped into another checkout -
        and it is also what a wrongly-open gate looks like. Topology cannot tell
        those apart, so this arm says so instead of pretending.

    WHAT THIS DOES NOT GUARANTEE: it never establishes that the gate SHOULD be
    shut. `test_the_corpus_gate_is_a_pure_read_of_the_one_import_time_measurement`
    carries the pinned-open and pinned-shut mutants, in every world.
    """
    toplevel = _repository_toplevel()
    reason = _corpus_gate_reason()
    if toplevel is None:
        assert reason is not None, (
            f"git resolves no repository at all from {REPO_ROOT}, so `git ls-files` here "
            "cannot have enumerated this corpus, yet the corpus gate is SHUT and every "
            "guard below will report a verdict on a tree nobody is entitled to one on"
        )
        return
    if reason is None:
        assert toplevel == REPO_ROOT or toplevel in REPO_ROOT.parents, (
            f"the corpus gate is SHUT, so `git ls-files` in {REPO_ROOT} printed this "
            f"tree's own anchored paths - but git resolves its work tree to {toplevel}, "
            "which neither is this directory nor contains it. One of the two is "
            "answering about some other tree"
        )
        return
    pytest.skip(
        "git resolves a repository here but the corpus gate is OPEN, and topology cannot "
        "separate a legitimate untracked copy inside another repository from a gate that "
        "is wrongly open - the pinned-open mutant is graded by "
        f"test_the_corpus_gate_is_a_pure_read_of_the_one_import_time_measurement instead: {reason}"
    )


def test_forcing_the_corpus_gate_open_skips_every_consumer_of_it(monkeypatch):
    """THE FORCED-OPEN DIRECTION, over every consumer rather than one of them.

    Runs in every world, including a tree with no repository at all. It is the
    half that proves the gate is WIRED to each helper - a gate proven pure and
    never proven wired is the recurrence this file has now paid for twice.
    """
    monkeypatch.setattr(
        "tests.test_line_endings._corpus_gate_reason",
        lambda: "forced: git does not enumerate this corpus",
    )
    for name, helper in _corpus_gate_consumers():
        with pytest.raises(BaseException) as caught:
            helper()
        assert isinstance(caught.value, _SKIPPED), (
            f"{name} did not consult the corpus gate; it raised "
            f"{type(caught.value).__name__}: {caught.value}"
        )
        assert "forced" in str(caught.value), (
            f"{name} skipped for some reason other than the gate: {caught.value}"
        )


def test_no_corpus_helper_skips_while_the_corpus_gate_is_closed():
    """THE MUTANT THAT SURVIVED THREE ROUNDS DIES HERE.

    Measured 2026-09-08 against the version this replaces: forcing
    `_plausible_corpus()`'s skip to fire unconditionally gave 25 passed, 11
    SKIPPED, EXIT=0, every skip at the same line. Eleven arms retired and the
    file still read green, because no arm anywhere asserted that a helper does
    NOT skip. "13 of 13 mutants die" was a claim about the doors somebody had
    thought to grade.

    So this asserts the absence of a skip, across every consumer of the gate,
    whenever the gate itself is shut. A helper whose skip is unconditional now
    reddens the file rather than quietly emptying it.

    AND IT SAYS SO WHEN IT CANNOT ESTABLISH THAT. Where the gate is open there
    is nothing here to grade, and this arm SKIPS with a reason naming that -
    rather than reporting an unqualified PASSED while checking nothing, which
    is what the docstring of the arm it replaces claimed it did and did not do.
    """
    gate = _corpus_gate_reason()
    if gate is not None:
        pytest.skip(
            "this arm grades helpers for skipping while the corpus gate is SHUT, and "
            f"the gate is open here, so there is nothing to grade: {gate}"
        )
    for name, helper in _corpus_gate_consumers():
        try:
            helper()
        except _SKIPPED as exc:
            pytest.fail(
                f"{name} SKIPPED although git enumerates this corpus, so every arm that "
                f"depends on it has silently stopped running: {exc}"
            )


def test_positive_control_the_real_check_attr_answer_is_accepted(monkeypatch):
    """WITHOUT THIS, A GUARD THAT REJECTED EVERY STREAM WOULD SATISFY THE ABOVE.

    The legitimate neighbour must survive the sweep: this replays the tree's
    OWN `check-attr` bytes through the stub and requires the full, real result.
    """
    tracked = _tracked_files()
    monkeypatch.setattr(subprocess, "run", _stub_check_attr(0, _real_check_attr_answer()))
    declared = _files_declared_lf()
    assert len(declared) >= _MIN_TRACKED_FILES, len(declared)
    assert len(declared) <= len(tracked)
    for anchor in _ENUMERATION_ANCHORS:
        assert anchor in declared, f"{anchor} vanished from an unmodified check-attr stream"


# ---------------------------------------------------------------------------
# THE IMPORT-TIME MEASUREMENT IS BOUNDED, AND ITS FAILURES ARE LEGIBLE
# ---------------------------------------------------------------------------

# The floor is a LITERAL for the reason `_MIN_TRACKED_FILES` is: sizing it from
# the scan it grades would make the scan agree with whatever it found, including
# nothing. Three direct `subprocess.run` calls were measured in this file on
# 2026-09-08 - the launcher, the check-attr sweep, and the positive control's
# replay - and a scan that finds fewer has stopped finding them.
_MIN_SUBPROCESS_LAUNCH_SITES = 3


def _subprocess_run_calls(source: str) -> list[ast.Call]:
    """Every literal `subprocess.run(...)` call in a chunk of Python source.

    A SOURCE-LEVEL SCAN ON PURPOSE, and it is the only shape that closes the
    door. The behavioural arms below prove that the launchers THIS FILE HAPPENS
    TO NAME are bounded, which is a statement about an enumerated tuple - and an
    enumerated tuple is exactly what let a mutant retire eleven arms earlier in
    this file's history. A new launch site added tomorrow appears in the AST
    whether or not anybody remembered to list it.
    """
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "run"
            and isinstance(func.value, ast.Name)
            and func.value.id == "subprocess"
        ):
            found.append(node)
    return found


def test_every_subprocess_launch_in_this_file_carries_a_deadline():
    """AN UNBOUNDED LAUNCH AT IMPORT CAN HANG THE COLLECTION OF THE WHOLE SUITE.

    Measured 2026-09-08 against the version this replaces, with `git ls-files`
    stalled at the subprocess layer: `import tests.test_line_endings` took
    12247ms for a 12s stall, produced no output and no diagnostic, and would
    have waited exactly as long as the stall lasted. `grep timeout=` over that
    version returned ZERO hits.
    """
    calls = _subprocess_run_calls(Path(__file__).read_text(encoding="ascii"))
    assert len(calls) >= _MIN_SUBPROCESS_LAUNCH_SITES, (
        f"the scan found only {len(calls)} `subprocess.run` calls in this file, under the "
        f"floor of {_MIN_SUBPROCESS_LAUNCH_SITES} - it is no longer finding the launch "
        "sites it is supposed to be grading, so its silence means nothing"
    )
    undeadlined = sorted(
        node.lineno for node in calls if not any(kw.arg == "timeout" for kw in node.keywords)
    )
    assert not undeadlined, (
        f"`subprocess.run` is called without `timeout=` at line(s) {undeadlined} of this "
        "file. A git that stops answering there blocks for as long as it stops answering, "
        "and at import that blocks collection of every test in the directory"
    )


def test_the_deadline_scanner_can_actually_see_a_missing_deadline():
    """THE NON-VACUITY ARM, both directions.

    Without this, a scanner that matched nothing at all would satisfy the arm
    above by finding no offender, and a scanner that matched everything would
    satisfy it by finding no `subprocess.run` either.
    """
    bounded = "import subprocess\nsubprocess.run(['git'], timeout=1)\n"
    unbounded = "import subprocess\nsubprocess.run(['git'])\n"
    unrelated = "import subprocess\nother.run(['git'])\nsubprocess.check_output(['git'])\n"

    assert len(_subprocess_run_calls(bounded)) == 1
    assert len(_subprocess_run_calls(unbounded)) == 1
    assert not _subprocess_run_calls(unrelated), (
        "the scanner matched something that is not `subprocess.run`, so its verdict on "
        "this file is about the wrong calls"
    )

    (bad,) = _subprocess_run_calls(unbounded)
    assert not [kw for kw in bad.keywords if kw.arg == "timeout"]
    (good,) = _subprocess_run_calls(bounded)
    assert [kw for kw in good.keywords if kw.arg == "timeout"]


@pytest.mark.parametrize(
    "raised,needle",
    [
        pytest.param(ValueError("injected"), "ValueError", id="a non-OSError"),
        pytest.param(OSError("no such tool"), "OSError", id="the one it used to catch"),
        pytest.param(
            subprocess.TimeoutExpired(["git", "ls-files"], 20.0),
            "did not answer within",
            id="the deadline expiring",
        ),
    ],
)
def test_a_git_that_will_not_answer_becomes_a_reason_string_not_a_traceback(
    monkeypatch, raised: Exception, needle: str
):
    """EVERY LAUNCH FAILURE LEAVES `_launch_git` AS TEXT.

    Measured 2026-09-08 against the version this replaces, whose catch was
    `except OSError` alone: a `ValueError` injected at the subprocess layer made
    `python -m pytest tests/test_line_endings.py` end in a RAW TRACEBACK and
    `Interrupted: 1 error during collection`, EXIT=2 - every test in the file
    gone, which is the precise outcome `tests/conftest.py` exists to remove, and
    a raw error string in an operator surface besides.
    """

    def boom(cmd, *args, **kwargs):
        raise raised

    monkeypatch.setattr(subprocess, "run", boom)
    call = _launch_git(["git", "ls-files"])
    assert call.failure is not None, "the launch failure was laundered into a clean result"
    assert needle in call.failure, call.failure
    assert "Traceback" not in call.failure


@pytest.mark.parametrize(
    "raised",
    [
        pytest.param(KeyboardInterrupt(), id="KeyboardInterrupt"),
        pytest.param(_SKIPPED("a stub asked to skip"), id="pytest.skip"),
    ],
)
def test_the_launcher_swallows_exception_and_not_base_exception(monkeypatch, raised):
    """THE COUNTERWEIGHT TO THE ARM ABOVE, and it is why the catch is narrowed.

    A launcher that caught `BaseException` would satisfy every legibility arm
    here and also eat the operator's Ctrl-C and any `pytest.skip` a stub raised
    on the way through. The broad catch is broad by exactly one step.
    """

    def boom(cmd, *args, **kwargs):
        raise raised

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(type(raised)):
        _launch_git(["git", "ls-files"])


def test_the_launcher_hands_its_deadline_to_subprocess(monkeypatch):
    """The AST arm proves a `timeout=` is WRITTEN; this proves one is PASSED."""
    seen: list[dict] = []

    def recording(cmd, *args, **kwargs):
        seen.append(kwargs)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", recording)
    _launch_git(["git", "ls-files"])
    assert seen, "the launcher made no subprocess call at all"
    assert seen[0].get("timeout") == _GIT_TIMEOUT_SECONDS, seen[0]
    assert seen[0].get("check") is False, (
        "the launcher asked subprocess to raise on a non-zero exit, which routes a real "
        "git verdict through the launch-failure branch and loses the exit code"
    )


def test_a_non_oserror_at_the_git_layer_fails_the_tracked_reader_rather_than_skipping_it(
    monkeypatch,
):
    """THE LEGIBLE OUTCOME IS STILL A LOUD ONE, and that is the other half.

    A launch failure that turned into a SKIP would be legible and would also
    retire every guard below it while reporting EXIT=0 - the failure mode this
    whole file is built against. git was present enough to be launched at, so
    `FAILED` is the honest disposition and it must reach the reader as red.
    """
    _require_a_repository_to_break()

    def boom(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and list(cmd[:2]) == ["git", "ls-files"]:
            raise ValueError("injected non-OSError")
        raise AssertionError(f"unexpected launch: {cmd}")

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(BaseException) as caught:
        _tracked_files()
    assert isinstance(caught.value, _FAILED), (
        f"_tracked_files() answered a launch failure with {type(caught.value).__name__} "
        f"rather than a loud failure: {caught.value}"
    )
    assert "ValueError" in str(caught.value), caught.value


def test_the_corpus_deriver_serves_the_import_time_measurement_not_a_live_tool(monkeypatch):
    """THE SAME PROPERTY THE GATE HAS, ONE HELPER OVER, AND IT WAS UNGRADED.

    `_plausible_corpus()`'s own docstring claims it "no longer runs git at all"
    and is "SERVED FROM THE IMPORT-TIME BASELINE", and the reason it gives is
    exact: a corpus deriver a stub can answer is grading the fixture. Measured
    2026-09-08, that claim had no arm behind it - a `_plausible_corpus` mutated
    to read a LIVE `_tracked_enumeration()` instead of `_BASELINE.enumeration`
    left this file at 48 passed, EXIT=0 in both a clone and a vendored copy.

    So the deriver is asked for its corpus with a `git ls-files` stub already
    installed that answers a plausible-sized decoy. A deriver reading the
    import-time measurement cannot see the stub; one that re-asks git returns
    the decoy, or nothing, and reddens here.
    """
    _require_a_repository_to_break()
    expected = list(_BASELINE.enumeration.files)
    assert expected, "the baseline holds no corpus, so this arm would grade nothing"
    monkeypatch.setattr(subprocess, "run", _stub_ls_files(0, "vendor/decoy.py\n" * 60))
    observed = [line for line in _plausible_corpus().splitlines() if line]
    assert observed == expected, (
        "_plausible_corpus() answered a `git ls-files` STUB rather than the measurement "
        f"taken at import - it returned {len(observed)} paths where the baseline holds "
        f"{len(expected)}. A corpus a stub can dictate grades the stub, not the classifier"
    )
