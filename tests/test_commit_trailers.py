"""No commit in this repository carries an agent trailer, and the hook proves it.

OPERATOR POLICY: this project never emits a `Co-Authored-By: Claude` trailer,
and never a `Claude-Session:` trailer either. CLAUDE.md states the first;
`.githooks/commit-msg` enforces it by STRIPPING rather than rejecting, so a
session that adds one out of habit still commits cleanly and the trailer simply
is not in the message that lands.

WHY THIS FILE EXISTS. Enforcement lived entirely in a hook, and a hook is local
config: `core.hooksPath` is not cloned, so a fresh clone runs ZERO hooks and the
policy silently does not apply there. That is not hypothetical here. Measured
2026-09-06, before the history rewrite that accompanied this file: TWO commits
carried both trailers - the root commit and one made later from the same cloud
clone. Neither clone had run `scripts/install_hooks.py`.

So the policy now has two enforcement points instead of one:

  1. The hook strips the trailer at commit time, on a clone that installed it.
  2. THIS TEST reads git history and fails if one ever lands anyway, on every
     clone, hooks or no hooks, and in CI.

A guard that only exists inside the thing it guards is not a guard.

THE SHALLOW-CLONE HOLE, and it was a real one. `.github/workflows/ci.yml` USED
TO check out at depth 1, so on that runner `git log` saw exactly one commit and
a full-history sweep there would have passed by construction while proving
nothing. A vacuous green is worse than a missing test, because it reads as
coverage. The history arm therefore DETECTS a shallow clone and skips with the
reason stated, rather than quietly sweeping a single commit and calling it
clean.

CI NOW CHECKS OUT AT DEPTH 0 on that lane, so the sweep runs there and the
Co-Authored-By hard rule is enforced by something other than a hook for the
first time. `tests/test_ci_history_depth.py` goes red if that depth returns to
a shallow value while this sweep still ships.

THE SKIP BRANCHES BELOW ARE NOT DEAD, and deleting them would break a lane.
`.github/workflows/docs-guards.yml` deliberately keeps depth 1, and its
selection is DERIVED at CI time from every test module mentioning a markdown
path - which is this module, twice. So it is collected and run SHALLOW on every
docs-only push, both branches fire there, and both are correct there.

AND A `git archive` EXTRACT IS NOT THE SAME POPULATION, though an earlier
draft of this paragraph said it was. Measured: an extract never reaches the
shallow branches at all. It is stopped one layer earlier by the
not-a-git-repository skip in the repo-root conftest, which reports 4 passed
and 4 skipped with trackedness as the stated reason.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import git_unusable_reason, require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Matched at the START of a line, case-insensitively, against the message body.
#: Anchored deliberately: a bare `grep -i co-authored-by` also matches prose
#: ABOUT the trailer, and this very docstring would trip it.
BANNED_TRAILER_PREFIXES = ("co-authored-by: claude", "claude-session:")

RECORD_SEP = chr(2)
FIELD_SEP = chr(1)


def _git(*args: str) -> str:
    require_git_repository()
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout


def _is_shallow() -> bool:
    return _git("rev-parse", "--is-shallow-repository").strip() == "true"


def banned_trailers_in(body: str) -> list[str]:
    """Every line of `body` that IS a banned trailer, not merely mentions one."""
    return [
        line.strip()
        for line in body.splitlines()
        if line.strip().lower().startswith(BANNED_TRAILER_PREFIXES)
    ]


def _history() -> list[tuple[str, str, str]]:
    raw = _git("log", f"--format=%H{FIELD_SEP}%s{FIELD_SEP}%b{RECORD_SEP}")
    records = []
    for chunk in raw.split(RECORD_SEP):
        chunk = chunk.strip()
        if not chunk:
            continue
        fields = chunk.split(FIELD_SEP)
        records.append((fields[0], fields[1], fields[2] if len(fields) > 2 else ""))
    return records


# ---------------------------------------------------------------------------
# The history sweep
# ---------------------------------------------------------------------------


def test_no_commit_in_history_carries_an_agent_trailer():
    if _is_shallow():
        pytest.skip(
            "shallow clone - a full-history sweep here would pass by construction, so "
            "this arm DECLINES TO MEASURE rather than sweeping one commit and calling it "
            "clean. This is not a verdict about the history. In a local clone, run `git "
            "fetch --unshallow` to re-arm it. In CI, check WHICH lane is shallow before "
            "changing any checkout depth - at least one lane in this tree is shallow "
            "deliberately, and raising it would be a regression rather than a fix"
        )

    offenders = []
    for sha, subject, body in _history():
        hits = banned_trailers_in(body)
        if hits:
            offenders.append(f"{sha[:7]} {subject[:50]} -> {'; '.join(hits)}")

    assert not offenders, "commits carry banned agent trailers: " + " | ".join(offenders)


def test_the_history_sweep_is_not_vacuous():
    """A sweep that stopped seeing commits would pass forever."""
    if _is_shallow():
        pytest.skip(
            "shallow clone - the history is truncated, so this non-vacuity floor would "
            "be measuring the clone depth rather than the sweep. It DECLINES TO MEASURE "
            "for the same reason as the arm above, and takes the same remedy"
        )
    assert len(_history()) >= 10


# ---------------------------------------------------------------------------
# The hook actually strips, end to end. Presence is not firing.
# ---------------------------------------------------------------------------


def _run_commit_msg_hook(message: str, tmp_path: Path) -> tuple[int, str]:
    """Run .githooks/commit-msg over a real message file and return the result."""
    # The hook is a GIT hook and shells out to git itself, so outside a
    # repository it exits 128 before reaching the trailer logic. Measured: the
    # arms below then fail with "the hook rejected an otherwise valid message",
    # which names the wrong cause entirely.
    require_git_repository()

    sh = shutil.which("sh")
    if sh is None:
        pytest.skip("no POSIX sh on PATH - the hook cannot be exercised here")

    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text(message, encoding="ascii", newline="\n")

    completed = subprocess.run(
        [sh, str(REPO_ROOT / ".githooks" / "commit-msg"), str(msg_file)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return completed.returncode, msg_file.read_text(encoding="utf-8")


def test_the_hook_strips_every_banned_trailer_it_is_handed(tmp_path):
    """Both trailer forms, together, in one message.

    The hook originally stripped only `Co-Authored-By: Claude`. Both forms
    appeared in this repository's history, from the same clone, so stripping one
    of the two left the policy half enforced.
    """
    code, result = _run_commit_msg_hook(
        "test(hooks): a valid subject the checker will accept\n"
        "\n"
        "A body that explains the change.\n"
        "\n"
        "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n"
        "Claude-Session: https://claude.ai/code/session_deadbeef\n",
        tmp_path,
    )

    assert code == 0, f"the hook rejected an otherwise valid message: {result}"
    assert banned_trailers_in(result) == [], f"trailers survived the hook: {result}"


def test_the_hook_leaves_an_ordinary_message_alone(tmp_path):
    """Stripping must not be over-eager - the body is otherwise untouched."""
    body = (
        "test(hooks): a valid subject the checker will accept\n"
        "\n"
        "A body that mentions the Co-Authored-By trailer in PROSE, which is not\n"
        "the same thing as carrying one, and must survive.\n"
    )
    code, result = _run_commit_msg_hook(body, tmp_path)
    assert code == 0
    assert "mentions the Co-Authored-By trailer in PROSE" in result


# ---------------------------------------------------------------------------
# Non-vacuity - prove each detector fires
# ---------------------------------------------------------------------------


def test_the_detector_fires_on_each_banned_form():
    for planted in (
        "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>",
        "co-authored-by: claude sonnet 5 <x@y>",
        "Claude-Session: https://claude.ai/code/session_01",
    ):
        assert banned_trailers_in(f"subject\n\nbody\n\n{planted}\n") == [planted.strip()]


def test_the_detector_does_not_fire_on_prose_about_a_trailer():
    """The anchor is the whole point.

    An unanchored `grep -i co-authored-by` matches this project's own docs,
    this test file, and the hook's own comments. That false positive is how a
    guard gets disabled.
    """
    prose = (
        "subject\n\nCLAUDE.md says never add a Co-Authored-By: Claude trailer,\n"
        "and the hook strips any Claude-Session: line it is handed.\n"
    )
    assert banned_trailers_in(prose) == []


def test_a_human_co_author_trailer_is_not_banned():
    """The policy is about AGENT trailers, not about co-authorship as such."""
    assert banned_trailers_in("subject\n\nCo-Authored-By: A Person <a@example.com>\n") == []


# ---------------------------------------------------------------------------
# The skip path must never become the normal path
# ---------------------------------------------------------------------------


def test_the_missing_git_skip_path_is_not_taken_in_a_real_checkout():
    """The sharpest arm in this file, and the reason it lives here.

    Every git-dependent guard under `tests/` now skips itself when
    `tests/conftest.py` reports no usable git. That is honest in a
    Download-ZIP copy and catastrophic anywhere else: if the helper ever
    answered "no git" inside a REAL checkout, all of those guards would
    evaporate at once and the suite would still report green. Vacuous green is
    worse than a missing test, because it reads as coverage - the same argument
    this module's docstring makes about the shallow-clone hole.

    So the helper is cross-checked against a SECOND, differently-derived
    signal: a `.git` entry on disk at or above the repo root. Disk presence is
    deliberately NOT how detection works, because it is wrong for a linked
    worktree, a submodule and a moved `GIT_DIR`. That independence is exactly
    what makes it a useful second opinion here - the two can only agree by
    both being right.

    BOTH ARMS ARE LIVE, each in the environment the other cannot reach. In a
    checkout the first arm proves the guards are still armed; in an archive
    extract the second proves the detector actually fires rather than being
    stuck on "usable". Assert only one and a detector welded to a single answer
    passes forever.
    """
    on_disk = [p for p in (REPO_ROOT, *REPO_ROOT.parents) if (p / ".git").exists()]
    reason = git_unusable_reason()

    if on_disk:
        assert reason is None, (
            f"a .git entry exists at {on_disk[0]}, so this IS a checkout, but the "
            f"shared helper reports git as unusable: {reason}. Every git-dependent "
            "guard under tests/ is silently skipping and this suite's green is "
            "meaningless"
        )
    else:
        assert reason is not None, (
            "no .git entry exists at or above the repo root, yet the shared helper "
            "reports git as usable - the detector is not detecting, and the guards "
            "that depend on it will fail with a confusing error instead of skipping"
        )
