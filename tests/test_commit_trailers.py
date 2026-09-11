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

import ast
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import NamedTuple

import pytest
from _pytest.outcomes import Skipped

from tests import conftest
from tests.conftest import git_unusable_reason, require_git_repository
from tools import git_subprocess_census as census

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

    THIS ARM IS UNGATED ON PURPOSE, AND THE REASON IS A SEAM RATHER THAN AN
    OVERSIGHT. With git hidden from both lookups it reports 1 failed / 7 passed
    / 5 skipped at exit 1, because a checkout whose `.git` is on disk while git
    the BINARY is missing takes the first branch below and `reason is None` is
    false. Read alone, that says the arm should call `require_git_repository()`.

    It must not, while `tests/test_conftest_skip_path_pinned.py` ships as it is.
    That module drives this exact function through `_expect_assertion_error`,
    which REJECTS `Skipped` BY NAME - "a skip is a green-looking non-result" -
    and pins that ANY non-None reason inside a checkout must REDDEN here.

    SIX ARMS THERE CARRY THAT, AND THEY ARE TWO POPULATIONS RATHER THAN ONE.
    FIVE are parametrised cases of
    `test_any_non_none_reason_inside_a_checkout_reddens_even_a_falsy_one`, with
    ids `x`, the empty string, a single space, `0` and `git is fine actually`.
    The SIXTH is a separate, non-parametrised arm,
    `test_a_reason_inside_a_checkout_reddens_and_the_message_carries_that_reason`.
    An earlier version of this paragraph called all six "parametrised reasons",
    which merges two populations into one and decays the moment either half
    moves.

    BOTH GATE PLACEMENTS REDDEN, AND AN EARLIER EITHER-OR HERE CLAIMED THEY
    MEASURE THE SAME. They do not. Each carries its own reading, measured over
    the whole `tests` suite on 2026-09-11:

      - INSIDE THE CHECKOUT BRANCH, immediately before its assert:
        6 failed / 2255 passed / 1 skipped, RETURNCODE 1, all six in
        `tests/test_conftest_skip_path_pinned.py` - exactly the six arms above.
      - AT THE TOP OF THIS FUNCTION, before the `.git` probe runs at all:
        8 failed / 2253 passed / 1 skipped, RETURNCODE 1. SEVEN in that module -
        the six above plus its
        `test_a_reason_with_no_disk_dot_git_is_a_pass_and_not_a_false_red` - and
        ONE here, this module's own arm of that same name. A gate that fires
        before the `.git` probe also takes the FORCED-SHAPE controls that drive
        the `else:` branch, which the checkout placement leaves standing.

    So the top placement is strictly worse than the checkout placement, and
    neither is available. The seam was ADJUDICATED on 2026-09-11; the ruling and
    the fact it rests on are in the section immediately below this function,
    where the fact is pinned as an ARM rather than left as prose.
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


# ---------------------------------------------------------------------------
# The adjudicated exemption for the arm above, recorded as an ARM
# ---------------------------------------------------------------------------
#
# ADJUDICATED 2026-09-11, against criteria written before either candidate was
# read. OUTCOME B: leave `test_the_missing_git_skip_path_is_not_taken_in_a_real
# _checkout` UNGATED and RECORD THE EXEMPTION. The runner-up - a
# not-runnable-only helper in `tests/conftest.py` so the two cases stop sharing
# one answer - lost because it turns this module's absent-git run into
# RETURNCODE 0, which is the vacuous green this whole line of work exists to
# prevent.
#
# WHY THE CONFLICT DISSOLVES rather than being traded off. The rule that gated
# the rest of this module has a population: SITES THAT SHELL GIT. That arm
# shells nothing. It CONSUMES `git_unusable_reason()` in order to AUDIT the
# helper, which is the opposite relationship. So the rule has already been
# applied here IN FULL, and the residual red under an absent git - 1 failed / 7
# passed / 5 skipped, RETURNCODE 1, measured 2026-09-11 - comes from the one
# site OUTSIDE that population. The arms it would have taken with it are not
# mis-scoped either: `tests/test_conftest_skip_path_pinned.py` reports 14 passed
# at RETURNCODE 0 under the same probe, being stub-driven and environment
# independent.
#
# THE RULING STANDS AND ITS CITATION DOES NOT, and those are separate things.
# RE-DERIVED PER SITE on 2026-09-11: this module holds THREE subprocess launches
# - in `_git`, `_run_commit_msg_hook` and `_lane_candidates` - and each of those
# three names `require_git_repository()` as a bare name on a line ABOVE its own
# launch. So "three sites, all gated" is true, and "no launch inside the exempt
# arm" is true of the module's text. What does NOT support either statement is
# the evidence the adjudicator cited for it: `census._guard_of` is a MODULE-LEVEL
# walk that answers GATED the moment the module NAMES one of the four helpers
# anywhere, an import line included, so it would have answered GATED for all
# three sites with every gate deleted. The ruling needs no reversal. Its citation
# needed re-deriving, and this is the re-derivation.
#
# AN UNEXPLAINED SECOND FAILURE, RECORDED AS UNEXPLAINED. A mutation pass that
# planted a `git status` launch inside the exempt arm reported a second failure,
# in `tests/test_moon_sync_responder.py`, and the builder who saw it attributed
# it to the planted launch touching live runtime records. THAT ATTRIBUTION IS
# REFUTED BY READING: that module contains no git call, no subprocess launch of
# git and no read of live `ops/runtime/` or `logs/`; its only git-adjacent match
# is the field name `m1_status`, and the arms concerned write solely into
# `tmp_path`. A later pass could not reproduce the failure and does not know
# which arm it was. RE-PROBED 2026-09-11 on this tree: that same mutant run over
# the whole `tests` suite reported 1 failed / 2261 passed / 1 skipped at
# RETURNCODE 1, the one failure being the arm below and nothing in
# `tests/test_moon_sync_responder.py`. A non-reproduction is not an
# explanation, so the cause stays UNKNOWN. It is written down here as unknown
# rather than left with a cause that reading disproves.
#
# A PROSE NOTE DECAYS. The premise is therefore pinned below instead: add a git
# launch to that function and the exemption stops being true, so the arm goes
# RED rather than silently covering it.
#
# STATED AS A LIMIT, NEVER ASSERTED. Nothing in this section says anything about
# what a PRESENT-but-BROKEN git must do. That is an open operator call, pinned
# open on purpose by `tests/test_conftest_git_gate.py`, and the adjudicator
# disqualified the gating outcome partly BECAUSE it would have answered that
# question by side effect - routing did-not-answer to SKIP.
#
# THE RESIDUAL THE ADJUDICATOR RECORDED, and it is part of the ruling rather
# than a caveat on it: if the operator ever rules SKIP on that open question,
# THIS EXEMPTION REOPENS and has to be decided again.

#: The one arm this module leaves ungated, named rather than located. A line
#: number here would decay on the next edit above it.
_EXEMPT_UNGATED_ARM = "test_the_missing_git_skip_path_is_not_taken_in_a_real_checkout"

#: The two `tests/conftest.py` helpers that actually DECIDE a skip.
#: `census.GUARD_NAMES` lists FOUR, and the other two - `git_unusable_reason`
#: and `classify_git_probe` - only PRODUCE A REASON. Folding those in would make
#: the exempt arm read as gated, since calling the first of them is exactly what
#: it does, so the distinction is the whole subject of this section.
_SKIP_DECIDING_HELPERS = frozenset({"require_git_repository", "skip_module_without_git"})


def _own_source() -> str:
    """This module's own bytes, which is what the census is run over."""
    return Path(__file__).resolve().read_text(encoding="utf-8")


class _ScopeFacts(NamedTuple):
    """Per-function spans, bare-name call sets, and gate-call line numbers."""

    spans: dict[str, tuple[int, int]]
    calls: dict[str, set[str]]
    gate_lines: dict[str, list[int]]


def _scope_facts(source: str) -> _ScopeFacts:
    """Per-function line spans, bare-name call sets and gate-call lines.

    A pure function of the source so the arm below can point it at synthetic
    sources whose answer is known, rather than only at this file.

    GATE CALLS ARE COLLECTED IN BOTH SPELLINGS. `require_git_repository()` and
    `conftest.require_git_repository()` are the same gate doing the same thing,
    and an earlier version of this helper saw only the first. Measured
    2026-09-11 against the second spelling substituted into `_git`: the arm
    below went RED on a gate that works, which is a false positive on correct
    code and the worst kind of guard. The attribute spelling is matched on its
    LAST component only, and only when that component is one of the two
    skip-deciding helper names, so an unrelated `obj.run()` adds no edge.
    """
    spans: dict[str, tuple[int, int]] = {}
    calls: dict[str, set[str]] = {}
    gate_lines: dict[str, list[int]] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        spans[node.name] = (node.lineno, getattr(node, "end_lineno", None) or node.lineno)
        named: set[str] = set()
        gates: list[int] = []
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            if isinstance(sub.func, ast.Name):
                named.add(sub.func.id)
                if sub.func.id in _SKIP_DECIDING_HELPERS:
                    gates.append(sub.lineno)
            elif isinstance(sub.func, ast.Attribute) and sub.func.attr in _SKIP_DECIDING_HELPERS:
                gates.append(sub.lineno)
        calls[node.name] = named
        gate_lines[node.name] = sorted(gates)
    return _ScopeFacts(spans, calls, gate_lines)


def _name_closure(seed: Iterable[str], calls: dict[str, set[str]]) -> frozenset[str]:
    """Close `seed` upwards over MODULE-LOCAL BARE-NAME CALL EDGES.

    NAME PRESENCE, NOT REACHABILITY, AND THE DISTINCTION IS LOAD-BEARING. The
    edges come from `ast.walk` over a whole function body, which has no order
    and no control flow, so "f names g" is all this can ever mean. The limits
    that buys are enumerated on the arm below rather than hidden here.

    A fixpoint rather than a recursion, so a cyclic call graph terminates.
    """
    reached = set(seed)
    changed = True
    while changed:
        changed = False
        for name, called in calls.items():
            if name not in reached and called & reached:
                reached.add(name)
                changed = True
    return frozenset(reached)


class _LaunchAudit(NamedTuple):
    """One module's launch sites, and who they belong to."""

    sites: tuple[census.CallSite, ...]
    facts: _ScopeFacts
    #: Sites held by at least one function span. Compared by COUNT against
    #: `sites`, which is the conservation check - see the arm below.
    attributed: tuple[census.CallSite, ...]
    #: Functions whose own span holds a launch.
    holding: frozenset[str]
    #: `holding` closed over call edges: a function that names one of them.
    launching: frozenset[str]
    #: Functions that name a skip-deciding helper, closed over the same edges.
    gate_naming: frozenset[str]
    #: Functions that name a gate only AFTER their first launch, by line.
    late_gates: tuple[str, ...]


def _audit_launches(source: str, path: str) -> _LaunchAudit:
    """Every subprocess launch in `source`, attributed to the functions holding it.

    ATTRIBUTION IS TO EVERY ENCLOSING FUNCTION, NOT THE INNERMOST ONE. A launch
    inside a nested `def` is genuinely held by the outer function too, and
    innermost-only attribution would let a nested `def` inside the exempt arm
    carry a launch the arm below then reports as clean. That case is one of the
    stubs. It is also why the conservation check below is AT LEAST ONE owner
    per site rather than exactly one: a nested launch legitimately has two.
    """
    sites = tuple(census.census_source(source, path))
    facts = _scope_facts(source)
    owners = [
        [name for name, (start, end) in facts.spans.items() if start <= site.lineno <= end]
        for site in sites
    ]
    attributed = tuple(site for site, held_by in zip(sites, owners) if held_by)
    holding = frozenset(name for held_by in owners for name in held_by)
    launching = _name_closure(holding, facts.calls)
    gate_naming = _name_closure(
        (name for name, lines in facts.gate_lines.items() if lines), facts.calls
    )
    late: list[str] = []
    for name in sorted(holding):
        lines = facts.gate_lines[name]
        if not lines:
            continue
        start, end = facts.spans[name]
        first_launch = min(site.lineno for site in sites if start <= site.lineno <= end)
        if min(lines) > first_launch:
            late.append(f"{name} (first gate line {min(lines)}, first launch line {first_launch})")
    return _LaunchAudit(
        sites, facts, attributed, holding, launching, gate_naming, tuple(late)
    )


#: The three ways a module's text can put the exempt arm back inside the
#: population of the shell-git rule. Each is a distinct MECHANISM and each is
#: driven by its own stub below; a repair that closed one and not the others
#: is exactly what the 2026-09-11 refutation found.
_LEXICAL = "LEXICAL"
_TRANSITIVE = "TRANSITIVE"
_UNATTRIBUTED = "UNATTRIBUTED"


def _exemption_complaints(audit: _LaunchAudit) -> list[str]:
    """Every reason the exempt arm's shells-nothing premise does NOT hold.

    An empty list is the premise holding. Each complaint is prefixed with the
    mechanism that produced it, so a stub caught for the wrong reason is a
    visible failure rather than a lucky pass.
    """
    out: list[str] = []
    span = audit.facts.spans.get(_EXEMPT_UNGATED_ARM)
    if span is not None:
        start, end = span
        inside = sorted(
            f"{site.callee} (bucket {site.bucket}) at line {site.lineno}"
            for site in audit.sites
            if start <= site.lineno <= end
        )
        if inside:
            out.append(f"{_LEXICAL}: a launch sits inside the arm's own span: {inside}")
    if _EXEMPT_UNGATED_ARM in audit.launching and _EXEMPT_UNGATED_ARM not in audit.holding:
        via = sorted(audit.facts.calls[_EXEMPT_UNGATED_ARM] & audit.launching)
        out.append(
            f"{_TRANSITIVE}: the arm names {via}, which launch(es) git in this same "
            "module, so the arm shells git through a module-local helper"
        )
    if len(audit.attributed) != len(audit.sites):
        held = {id(site) for site in audit.attributed}
        lost = sorted(
            f"{site.callee} at line {site.lineno}"
            for site in audit.sites
            if id(site) not in held
        )
        out.append(
            f"{_UNATTRIBUTED}: the census found {len(audit.sites)} launch site(s) and "
            f"{len(audit.attributed)} were held by a function span, so {lost} belong to "
            "no function and are audited neither for nor against the exemption"
        )
    return out


#: STUBS THAT VARY MORE THAN ONE POSITION, which is the whole point of them.
#: The previous single stub varied the ONE position its own mutant varied - a
#: bare `def`, no decorator, the launch as the first body statement, literal
#: argv, dotted `subprocess.run` - and was byte-for-byte the shape the detector
#: already caught. A decoy that varies one position pins one position, and the
#: 2026-09-11 refutation walked in through every position it held fixed.
#:
#: Each entry is (label, expected mechanism, source). The source is TEXT and is
#: never executed, so an import that would not resolve at runtime is fine.
_EXEMPT_ARM_LAUNCH_STUBS = (
    (
        "literal argv, dotted subprocess.run, first statement of the body",
        _LEXICAL,
        "import subprocess\n"
        "\n"
        "\n"
        "def " + _EXEMPT_UNGATED_ARM + "():\n"
        '    subprocess.run(["git", "status"], capture_output=True)\n',
    ),
    (
        "aliased module, argv bound to a name, args= keyword, not the first statement",
        _LEXICAL,
        "import subprocess as sp\n"
        "\n"
        "\n"
        "def " + _EXEMPT_UNGATED_ARM + "():\n"
        "    note = 'an ordinary statement first'\n"
        '    argv = ["git", "rev-parse", "HEAD"]\n'
        "    sp.run(args=argv, capture_output=True)\n"
        "    return note\n",
    ),
    (
        "from-imported check_output, called by bare name",
        _LEXICAL,
        "from subprocess import check_output\n"
        "\n"
        "\n"
        "def " + _EXEMPT_UNGATED_ARM + "():\n"
        '    return check_output(["git", "log", "-1"])\n',
    ),
    (
        "launch inside a nested def within the arm, which innermost-only attribution drops",
        _LEXICAL,
        "import subprocess\n"
        "\n"
        "\n"
        "def " + _EXEMPT_UNGATED_ARM + "():\n"
        "    def _inner():\n"
        '        subprocess.run(["git", "status"], capture_output=True)\n'
        "\n"
        "    _inner()\n",
    ),
    (
        "launch reached through a module-local helper the arm names",
        _TRANSITIVE,
        "import subprocess\n"
        "\n"
        "\n"
        "def _git(*args):\n"
        '    return subprocess.run(["git", *args], capture_output=True)\n'
        "\n"
        "\n"
        "def " + _EXEMPT_UNGATED_ARM + "():\n"
        '    _git("status", "--porcelain")\n'
        "    return None\n",
    ),
    (
        "launch in a DECORATOR, which sits ABOVE the def line and so above the span",
        _UNATTRIBUTED,
        "import subprocess\n"
        "\n"
        "import pytest\n"
        "\n"
        "\n"
        "@pytest.mark.skipif(\n"
        '    subprocess.run(["git", "status"], capture_output=True).returncode == 99,\n'
        '    reason="never fires",\n'
        ")\n"
        "def " + _EXEMPT_UNGATED_ARM + "():\n"
        "    return None\n",
    ),
)

#: THE CONTROL, and without it every stub above could be reddening merely
#: because the module contains a launch at all. Here one does - in `_launcher`,
#: which the arm never names - and the expected answer is NO COMPLAINT.
_EXEMPT_ARM_CLEAN_STUB = (
    "import subprocess\n"
    "\n"
    "\n"
    "def _launcher():\n"
    '    return subprocess.run(["git", "status"], capture_output=True)\n'
    "\n"
    "\n"
    "def " + _EXEMPT_UNGATED_ARM + "():\n"
    "    return git_unusable_reason()\n"
)


def test_the_exempt_arm_launches_no_git_and_every_launch_here_names_a_gate() -> None:
    """THE ADJUDICATED EXEMPTION, PINNED AS THE FACT IT RESTS ON.

    Two halves, and they are different strengths on purpose.

    HALF ONE IS THE EXEMPTION'S PREMISE. `tools/git_subprocess_census.py` finds
    no subprocess launch that the exempt arm holds - not inside its own span,
    not through a module-local helper it names, and no launch anywhere in this
    module that belongs to no function at all. That is what puts it OUTSIDE the
    population of the shell-git rule. Add a launch by any of those three routes
    and this half reddens.

    HALF TWO IS THAT THE RULE IS APPLIED HERE IN FULL. Every function that DOES
    hold a launch must NAME one of the two skip-deciding helpers, itself or
    through a module-local function it names.

    WHAT "NAMES" MEANS, AND IT IS NOT "REACHES". The call edges come from
    `ast.walk` over a whole function body. There is no ordering and no control
    flow in that, so this arm can only ever assert NAME PRESENCE. Three shapes
    therefore read as gated here while behaving otherwise, each measured
    2026-09-11 by substituting it into `_git` and running this arm:

      - A GATE PLACED AFTER THE LAUNCH. Behaviourally this is the defect the
        rule exists to prevent: with `require_git_repository()` below
        `subprocess.run(..., check=True)`, `_git` under an absent git RAISES
        instead of skipping. Name presence alone read that as gated. THIS ONE
        IS NOW CAUGHT, by a cheap line-number comparison rather than by control
        flow - the first gate line in a launching function must precede its
        first launch line. The comparison is per function and by LINE, so it
        says nothing about a gate in a branch that does not execute.
      - A GATE UNDER `if False:` - still a bare name in the body, still reads
        as gated, NOT CAUGHT. Catching it needs control-flow analysis.
      - A GATE INSIDE A NESTED `def` THAT IS NEVER CALLED - same, NOT CAUGHT.
        `ast.walk` descends into the nested body and collects the name.

    Those two are named as limits rather than papered over. An honest narrow
    claim beats a broad one that is false.

    THE CALL GRAPH IS MODULE-LOCAL. An edge exists only to a function DEFINED
    in this module, so a call into an imported function that launches git is
    invisible here. That is not a hole in the exemption: the census is over
    this module's own bytes, and the exempt arm's relationship to
    `git_unusable_reason()` - consuming it to AUDIT it - is the thing that was
    adjudicated, not something this arm re-decides.

    THE CENSUS `guard` COLUMN CANNOT CARRY HALF TWO, and that is measured
    rather than assumed: `census._guard_of` walks the WHOLE module and answers
    GATED if the module NAMES any of the four helpers ANYWHERE, so all three
    launch sites in this file report `guard='GATED'` and would keep reporting
    it after a gate was deleted from any one of them. Measured 2026-09-11. So
    half two derives per-function name presence here instead of reading that
    column, and the column is not consulted at all.

    CONSERVATION IS AN ASSERTION AND NOT AN INVARIANT, because it has already
    failed once. `node.lineno` for a decorated `FunctionDef` is the `def` line,
    so a decorator sits ABOVE the span. A launch planted in a decorator on the
    exempt arm was COUNTED by the census - three sites became four - and then
    dropped by both halves: outside every span, so half one reported clean, and
    owned by no function, so half two never audited it. Measured 2026-09-11.
    The repair is not a decorator special case; it is the count check below,
    which is the only shape that catches a drop whatever caused it.

    NON-VACUITY IS BUILT IN rather than left to a mutation pass: the span
    lookup has to have found a real, non-degenerate span, the census has to
    have found launches at all, some function has to hold one, every stub in
    `_EXEMPT_ARM_LAUNCH_STUBS` has to be caught BY ITS OWN MECHANISM, and the
    clean control stub - which does contain a launch, in a function the arm
    never names - has to be caught by none of them.

    THIS ARM ASSERTS NOTHING ABOUT A PRESENT-BUT-BROKEN GIT. That is an open
    operator call. If the operator ever rules SKIP on it, the exemption
    recorded above REOPENS and this arm is what has to be revisited.
    """
    audit = _audit_launches(_own_source(), "tests/test_commit_trailers.py")
    spans = audit.facts.spans

    assert _EXEMPT_UNGATED_ARM in spans, (
        f"{_EXEMPT_UNGATED_ARM} is not defined in this module, so the exemption "
        "recorded above names a function that no longer exists and every assertion "
        f"below it would be about nothing: {sorted(spans)[:8]}"
    )
    start, end = spans[_EXEMPT_UNGATED_ARM]
    assert end > start, (
        "the exempt arm's derived span is a single line, so 'no launch inside it' is "
        "true of almost any file and this arm has stopped measuring: "
        f"{(start, end)}"
    )

    assert audit.sites, (
        "the census found NO subprocess launch anywhere in this module, so both halves "
        "below are assertions over an empty set and cannot fail. Either the launches "
        "are gone - in which case the gating this section records is moot and the "
        "section should go - or the census stopped seeing them"
    )

    assert len(audit.attributed) == len(audit.sites), (
        f"CONSERVATION: the census counted {len(audit.sites)} launch site(s) in this "
        f"module and only {len(audit.attributed)} of them fall inside any function's "
        "span. The leftovers are attributed to nobody, so no per-function claim below "
        "covers them - which is exactly how a launch planted in a DECORATOR was "
        "counted and then dropped by both halves. Attribute them or remove them; do "
        "NOT drop the count check"
    )

    complaints = _exemption_complaints(audit)
    assert not complaints, (
        f"{_EXEMPT_UNGATED_ARM} no longer shells nothing: {complaints}. The "
        "adjudicated exemption recorded above rests on that function launching no git "
        "- it CONSUMES git_unusable_reason() to AUDIT the helper - so a launch it "
        "holds, by any of those routes, puts it back INSIDE the population the gating "
        "rule covers and the exemption no longer holds. Remove the launch, or re-open "
        "the seam and adjudicate it again. Do NOT widen this arm to tolerate it"
    )

    assert audit.holding, (
        f"the census reported {len(audit.sites)} launch site(s) and none of them fell "
        "inside any function's span, so the attribution step matched nothing and half "
        "two below is vacuous"
    )
    ungated = sorted(audit.launching - audit.gate_naming)
    assert not ungated, (
        f"{ungated} launch a subprocess in this module, directly or through a "
        f"module-local function they name, with no {sorted(_SKIP_DECIDING_HELPERS)} "
        "named anywhere on that path - so those sites FAIL rather than skip when git "
        "is unreachable. The exemption above is specifically for the ONE arm that "
        "shells nothing; it is not cover for a site that does"
    )
    assert not audit.late_gates, (
        f"{list(audit.late_gates)} name a gate only AFTER their own first launch. "
        "Name presence would have read that as gated, and it is not: a gate below "
        "`subprocess.run(..., check=True)` never runs, so the function RAISES under an "
        "absent git instead of skipping. Move the gate above the launch"
    )

    for label, mechanism, stub in _EXEMPT_ARM_LAUNCH_STUBS:
        stub_complaints = _exemption_complaints(_audit_launches(stub, f"<stub {label}>"))
        assert stub_complaints, (
            f"the detector found nothing wrong with the stub '{label}', in which a "
            "launch IS held by a function of the exempt name. Its empty answer about "
            "this file therefore measured the detector rather than the file"
        )
        assert any(text.startswith(mechanism) for text in stub_complaints), (
            f"the stub '{label}' was caught, but not by {mechanism} - the mechanism it "
            f"exists to exercise: {stub_complaints}. A stub caught by the wrong "
            "mechanism leaves its own mechanism unpinned"
        )

    control = _exemption_complaints(_audit_launches(_EXEMPT_ARM_CLEAN_STUB, "<clean stub>"))
    assert not control, (
        f"the CONTROL stub was reported dirty: {control}. It contains a launch, in a "
        "function the exempt arm never names, and the correct answer is no complaint. "
        "A detector that complains here is complaining about the presence of a launch "
        "anywhere, so every stub above passes for a reason that has nothing to do with "
        "the exempt arm"
    )


# ---------------------------------------------------------------------------
# The archive branch of that cross-check, driven from THIS file
# ---------------------------------------------------------------------------
#
# MEASURED, and the whole reason this section exists. A line-level trace over
# `python -m pytest tests/test_commit_trailers.py` at b5dc138 recorded lines
# 263, 264, 266 and 267 of this module as HIT and nothing at all between 268
# and 278 - the `else:` arm of the cross-check above never executed. The same
# trace over the whole `tests` suite DID reach it, at 274, 275 and 278, because
# `tests/test_conftest_skip_path_pinned.py` forces the shape from outside.
#
# So the branch is NOT structurally dead, and an earlier hand-off saying so was
# wrong. It is dead under ISOLATED SELECTION - and one real lane selects this
# module in isolation. `.github/workflows/docs-guards.yml` derives its selection
# from tracked test modules that mention a markdown path; this module matches
# that pattern twice and the pinning module matches it zero times, so on every
# docs-only push the `else:` arm ships collected and unexercised. Those line
# numbers are a record of one measurement at one commit and will decay - the
# branch is named by its function above, not by its line.
#
# The technique below is the pinning module's, RE-IMPLEMENTED rather than
# imported. Importing it would make this file depend on the file whose job is
# to audit this file, and the two are supposed to be separately derived.

#: The GENUINE `@lru_cache(maxsize=1)` wrapper, captured at import time before
#: any arm can stub the name. Cache clearing has to go through this object:
#: once a stub lambda is bound in its place the name has no `cache_clear` at
#: all, and reaching for it by name in teardown would die with AttributeError
#: while leaving the real cache holding a stubbed answer.
_REAL_GIT_UNUSABLE_REASON = git_unusable_reason

#: A reason distinctive enough that its presence proves the arm was handed THIS
#: value rather than having found some reason of its own.
_ARCHIVE_SENTINEL_REASON = "SENTINEL-4d5e6f: git is unusable and this is the reason handed in"


@pytest.fixture
def real_reason_cache_cleared() -> Iterator[None]:
    """Clear the real helper's cache on both sides of an arm that stubs it.

    Cleared BEFORE so no arm here inherits an answer another test cached from a
    real probe, and AFTER so nothing later in the suite reads an answer cached
    while a stub was installed.

    OPT-IN, AND DELIBERATELY NOT AUTOUSE. The reason recorded here previously -
    that the arms above must run against the real tree - was not the operative
    one, and it does not survive reading the body: this fixture only clears a
    cache and stubs nothing, so autouse would not have taken any arm off the
    real tree.

    THE OPERATIVE REASON IS FALSE SYMMETRY. `tests/test_conftest_skip_path_pinned.py`
    carries a neutraliser that IS autouse and does strictly MORE than this one:
    it deletes `GIT_DIR` and `GIT_WORK_TREE` for every arm in that file as well
    as clearing the cache. Here the environment deletion lives in
    `_stub_reason()` instead. Two fixtures that were autouse alike, named alike
    and neutralised DIFFERENT things would read as one mechanism to the next
    person who diffs them, and a silent divergence between two hand
    transcriptions of one claim is a failure this tree has already been bitten
    by. Opt-in keeps the difference visible at every call site.

    MEASURED, NOT REASONED. Flipping this decorator to `autouse=True` was run
    and reverted on 2026-09-10: this module alone and the whole `tests` suite
    reported IDENTICAL pass and skip counts either way, and both held with
    `GIT_DIR` exported to a different git directory. The counts themselves are
    not restated here - they decay on the next arm added, and the EQUALITY is
    the finding. Autouse is behaviour-neutral here, so it buys nothing that
    would pay for the false symmetry above.

    THE HONEST REPAIR IS NOT IN THIS FILE. One shared neutraliser in
    `tests/conftest.py`, consumed by both modules, is what removes the second
    transcription altogether rather than making the two copies look more alike.
    That lands in files this one cannot reach.
    """
    _REAL_GIT_UNUSABLE_REASON.cache_clear()
    yield
    _REAL_GIT_UNUSABLE_REASON.cache_clear()


def _force_archive_shape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Repoint THIS module's `REPO_ROOT` at a directory with no `.git` above it.

    The absence is ASSERTED, never assumed. If a `.git` entry existed anywhere
    up the temporary path the cross-check would take its CHECKOUT branch, and
    the arm would grade the other half while reporting green.
    """
    root = tmp_path / "archive_shape"
    root.mkdir()
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", root)
    found = [p for p in (root, *root.parents) if (p / ".git").exists()]
    assert not found, (
        f"precondition failed: a .git entry exists at {found[0] if found else None}, at or "
        f"above {root}, so the archive branch is not reachable from here and this arm would "
        "grade the checkout branch instead"
    )
    return root


def _stub_reason(monkeypatch: pytest.MonkeyPatch, reason: str | None) -> None:
    """Make `git_unusable_reason()` answer `reason` at BOTH of its bindings.

    THIS module's global is what the cross-check's own body calls, because the
    name was imported into this namespace at import time. `tests.conftest`'s
    global is the DEFINITION site, and it is what `require_git_repository()`
    resolves when it looks the name up in its own module globals. Patch only
    the first and the world is split-brained: the cross-check's arithmetic and
    any helper it may later call disagree about whether git works, and an arm
    can then pass while grading a world that does not exist. Both get the SAME
    value so the forced world is internally coherent.

    GIT_DIR and GIT_WORK_TREE are deleted here as well. Exported, they are the
    disposition in which git answers successfully for a tree that has no `.git`
    on disk, which would let the ambient environment decide an arm. Nothing
    below shells out to git once both bindings are stubbed, so they cannot
    decide these arms today - deleting them means they cannot decide them after
    a later edit either.
    """
    monkeypatch.delenv("GIT_DIR", raising=False)
    monkeypatch.delenv("GIT_WORK_TREE", raising=False)
    _REAL_GIT_UNUSABLE_REASON.cache_clear()
    monkeypatch.setattr(conftest, "git_unusable_reason", lambda: reason)
    monkeypatch.setattr(sys.modules[__name__], "git_unusable_reason", lambda: reason)


def _expect_assertion_error(fragment: str) -> str:
    """Run the cross-check, demanding an AssertionError that carries `fragment`.

    Catches `BaseException` and rejects `Skipped` BY NAME. `Skipped` derives
    from `BaseException`, so `pytest.raises(AssertionError)` - and even
    `pytest.raises(Exception)` - lets a skip straight through, and a skip
    escaping here would read as a green non-result rather than as the arm
    having stopped guarding.
    """
    try:
        test_the_missing_git_skip_path_is_not_taken_in_a_real_checkout()
    except Skipped as skipped:
        raise AssertionError(
            f"the cross-check SKIPPED instead of failing: {skipped!r}. A skip is a "
            "green-looking non-result, so the arm that guards every git-dependent guard "
            "under tests/ would silently stop guarding"
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
        "the cross-check PASSED where it must fail. Its archive branch is the half that "
        "reports a detector welded to 'usable', and a pass here means that half is gone"
    )


def _expect_no_raise(what: str) -> None:
    """Run the cross-check, demanding it complete - it must not be a false red."""
    try:
        test_the_missing_git_skip_path_is_not_taken_in_a_real_checkout()
    except Skipped as skipped:
        raise AssertionError(f"{what}: the cross-check skipped rather than passing: {skipped!r}") from skipped
    except BaseException as failure:
        raise AssertionError(
            f"{what}: the cross-check raised {type(failure).__name__} on a shape it must "
            f"accept - that is a false red: {failure!r}"
        ) from failure


def test_the_dot_git_probe_cannot_tell_a_worktree_file_from_a_checkout_directory(tmp_path: Path) -> None:
    """The MECHANISM that makes the archive branch need forcing, asserted.

    `(p / ".git").exists()` answers True for a DIRECTORY, which is an ordinary
    checkout, and equally True for a FILE, which is the shape a linked worktree
    has - and this repository is worked in linked worktrees. There is therefore
    no shape of a real checkout in which the cross-check's list comprehension
    comes back empty, which is why the two arms below have to force the shape
    rather than wait for a `git archive` extract to turn up. If that ever stops
    holding, this arm reddens and the reasoning above has to be rewritten.
    """
    as_directory = tmp_path / "ordinary_checkout"
    (as_directory / ".git").mkdir(parents=True)
    as_file = tmp_path / "linked_worktree"
    as_file.mkdir()
    (as_file / ".git").write_bytes(b"gitdir: ../elsewhere/.git/worktrees/x\n")
    absent = tmp_path / "archive_extract"
    absent.mkdir()

    assert (as_directory / ".git").is_dir(), "precondition: the checkout shape must be a directory"
    assert (as_file / ".git").is_file(), "precondition: the worktree shape must be a file"

    assert (as_directory / ".git").exists()
    assert (as_file / ".git").exists(), (
        "a linked worktree's .git is a FILE. If exists() stopped answering True for it, the "
        "cross-check would take its ARCHIVE branch inside a real checkout and demand a reason "
        "from a tree whose git works perfectly"
    )
    assert not (absent / ".git").exists(), (
        "control, and without it the three assertions above are satisfied by a probe welded "
        "to True: the same call must answer False where no .git entry exists"
    )


def test_a_usable_git_with_no_disk_dot_git_reddens_the_archive_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, real_reason_cache_cleared: None
) -> None:
    """Drive the `else:` arm above and require it to FIRE.

    This is the proposition that branch exists to carry: in a tree with no
    `.git` anywhere at or above the root, a helper still answering "git is
    usable" is a detector welded to one answer, and every guard depending on it
    would fail with a confusing error rather than skipping. Delete the `else:`
    block, or flip its `is not None` to `is None`, and this arm reddens.
    """
    _force_archive_shape(monkeypatch, tmp_path)
    _stub_reason(monkeypatch, None)
    _expect_assertion_error("the detector is not detecting")


def test_a_reason_with_no_disk_dot_git_is_a_pass_and_not_a_false_red(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, real_reason_cache_cleared: None
) -> None:
    """The control for the arm above, and the second of the two guards.

    An honest archive extract - no `.git` on disk, and a helper that says so -
    is the exact shape the whole SKIP mechanism exists to serve. Reddening here
    would be the false red that trains a reader to ignore red, and without this
    arm an `else:` welded to `assert False` would satisfy the arm above.
    """
    _force_archive_shape(monkeypatch, tmp_path)
    _stub_reason(monkeypatch, _ARCHIVE_SENTINEL_REASON)
    _expect_no_raise("an archive extract whose helper reports an honest reason")


# ---------------------------------------------------------------------------
# The selector of the docs-only lane, reproduced and asserted
# ---------------------------------------------------------------------------
#
# THE RATIONALE FOR THE SECTION ABOVE RESTS ON AN INCIDENTAL STRING, and until
# these two arms landed nothing anywhere guarded it.
#
# `.github/workflows/docs-guards.yml` builds its test selection in two moves: at
# its `git ls-files -z` line, and at the `grep -qE` line inside the loop that
# reads the result. A tracked module under a `tests/` directory is a CANDIDATE,
# and a candidate is SELECTED if and only if some LINE of it matches the
# workflow's markdown-path pattern. That is a filter on TEXT and on nothing
# else.
#
# This module matches that pattern exactly twice, and BOTH matches are
# incidental prose naming the operator-policy document - one in the docstring at
# the top of this file, one inside a fixture's commit-message string further
# down. NEITHER of them opens that document, or any document. Reword either
# mention and this module silently leaves the lane; the two arms above then
# guard a lane they no longer ship on, and the section header above becomes a
# false statement with nothing anywhere to say so.
#
# The proposition worth pinning is therefore the CONDITIONAL one, and it has two
# halves. This module IS in that lane, AND the module that drives the `else:`
# arm cross-module IS NOT - which is exactly why the two forced-shape arms above
# have to exist at all. The second half is MEASURED below, by running the same
# selector over that module, rather than taken on the word of the comment above.
#
# THE WORKFLOW IS THE SOURCE. Everything here is a transcription of it. If the
# two ever disagree, the workflow wins and this section is what changes.

#: The lane's content filter, transcribed from the workflow's `grep -qE` line.
#:
#: BUILT BY CONCATENATION, AND THAT IS NOT A STYLE CHOICE. Written as a single
#: literal, this pattern's own source text contains a match for it: a dot, the
#: two letters, then an open parenthesis, which is not alphanumeric. The module
#: would then be selected by the lane BECAUSE THIS SECTION IS IN IT, the first
#: arm below would pass no matter what the rest of the file said, and the
#: fragility it exists to report would be concealed by the report. Splitting the
#: literal keeps that adjacency out of these bytes, and the second arm below
#: MEASURES that it stayed out rather than trusting this comment.
_LANE_CONTENT_PATTERN = re.compile(r"\." + "md" + r"([^a-zA-Z0-9]|$)")

#: The two pathspecs the lane hands `git ls-files`, from the same workflow step.
#: The `-z` is preserved for the workflow's own reason: without it a path
#: carrying a space or a quote does not survive the split.
_LANE_PATHSPECS = ("*/tests/*.py", "tests/*.py")

#: The module whose arms drive this module's archive branch cross-module. The
#: entire justification for the two forced-shape arms above is that this module
#: is NOT selected by the lane, so on a docs-only push that branch ships
#: collected and unexercised.
_CROSS_MODULE_DRIVER = "tests/test_conftest_skip_path_pinned.py"

#: Its FIRST occurrence in this file is the section header a few lines up, so
#: partitioning the source on it splits the file into everything written before
#: this section and everything written as part of it. The self-reference arm
#: asserts the marker was found, so rewording the header reddens that arm rather
#: than silently splitting at nothing.
_LANE_SECTION_MARKER = "The selector of the docs-only lane, reproduced and asserted"


def _lane_candidates() -> list[str]:
    """The lane's candidate list, re-derived from the tracked index.

    GIT_DIR AND GIT_WORK_TREE ARE SCRUBBED FROM THE CHILD ENVIRONMENT. Exported,
    either one points `git ls-files` at a different index entirely - the
    disposition in which git answers successfully about a tree that is not this
    one - and these arms would grade some other file list while reporting on
    this module. The lane runs on a fresh checkout with neither variable set, so
    scrubbing is what makes the reproduction FAITHFUL rather than what makes it
    differ.
    """
    require_git_repository()
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    completed = subprocess.run(
        ["git", "ls-files", "-z", *_LANE_PATHSPECS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert completed.returncode == 0, (
        f"`git ls-files` exited {completed.returncode} once GIT_DIR and GIT_WORK_TREE "
        f"were scrubbed, though the shared helper reports git as usable here. That "
        f"combination means the ambient environment was deciding what this tree's index "
        f"contains: {completed.stderr.strip()!r}"
    )
    return [path for path in completed.stdout.split(chr(0)) if path]


def _lane_selects(text: str) -> bool:
    """Apply the lane's content filter to `text` the way `grep -qE` does.

    LINE BY LINE, and the split is load-bearing. The pattern's `$` alternative
    anchors at the end of a LINE for grep, while one `re.search` over an entire
    file body would anchor it only at the end of the FILE. Splitting first is
    what makes the two agree.
    """
    return any(_LANE_CONTENT_PATTERN.search(line) for line in text.splitlines())


def _module_relative_path() -> str:
    """This module's path, spelled the way the tracked index spells it."""
    return Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()


def test_this_module_is_in_the_docs_lane_and_its_cross_module_driver_is_not() -> None:
    """Both halves of the conditional the section above depends on, measured.

    Reword either incidental mention in this file and the third assertion below
    goes red - which is the entire point, because that reword is silent
    everywhere else in the tree.
    """
    candidates = _lane_candidates()
    here = _module_relative_path()

    assert here in candidates, (
        f"{here} is not in the lane's candidate list. Either it is untracked, or the "
        f"workflow's pathspecs stopped covering it - and either way the arms above are "
        f"guarding a lane this module never reaches"
    )
    assert _CROSS_MODULE_DRIVER in candidates, (
        f"{_CROSS_MODULE_DRIVER} is not a candidate at all, so the interesting half "
        f"below - that the CONTENT filter is what excludes it - would be satisfied for "
        f"the wrong reason. Measured rather than assumed, precisely so that cannot pass "
        f"quietly"
    )

    selected = []
    for path in candidates:
        candidate = REPO_ROOT / path
        if not candidate.is_file():
            # `grep -qE` against an unreadable path exits non-zero, and the
            # workflow's `|| continue` treats that as "not selected". Mirrored
            # here so a tracked-but-absent path cannot make this list disagree
            # with the lane's.
            continue
        if _lane_selects(candidate.read_text(encoding="utf-8", errors="replace")):
            selected.append(path)

    assert here in selected, (
        f"{here} no longer matches the lane's content filter, so the docs-only lane has "
        f"stopped collecting it. The two forced-shape arms above exist ONLY because that "
        f"lane runs this module in ISOLATION, without the module that drives the branch "
        f"cross-module, and that rationale is now false"
    )
    assert _CROSS_MODULE_DRIVER not in selected, (
        f"{_CROSS_MODULE_DRIVER} is now selected by the lane as well, so it runs "
        f"alongside this module there and drives the archive branch itself. The "
        f"forced-shape arms above are not wrong, but the reason recorded for them is"
    )
    assert len(selected) < len(candidates), (
        f"control: all {len(candidates)} candidates came back selected, so the content "
        f"filter transcribed here is filtering nothing and the assertions above say "
        f"nothing about the lane"
    )


def test_the_lane_membership_of_this_module_is_not_manufactured_by_this_section() -> None:
    """The self-reference control, and it is not optional.

    An arm asserting something about its OWN source file can make its assertion
    true merely by containing the text it looks for. Here that failure would be
    total: the lane's filter reads TEXT, this section is text inside the file
    the filter reads, and one unsplit copy of the pattern anywhere below would
    select the module by itself. The arm above would then stay green through any
    reword of the two prose mentions it was written to protect.

    So the source is split at this section's header and the halves are graded
    separately. Everything written BEFORE the section must carry the membership;
    everything written AS PART OF the section must carry none of it.
    """
    text = Path(__file__).resolve().read_text(encoding="utf-8")
    head, marker, tail = text.partition(_LANE_SECTION_MARKER)

    assert marker, (
        f"the section header {_LANE_SECTION_MARKER!r} is not in this file, so the split "
        f"would put the whole source in one half and grade nothing"
    )
    assert _lane_selects(head), (
        "the incidental mentions that put this module in the lane are gone from "
        "everything above this section, so whatever keeps it in the lane now is this "
        "section itself"
    )
    assert not _lane_selects(tail), (
        "this section's own text matches the lane's content filter. The arm above is "
        "then true because it exists rather than because of the two incidental mentions "
        "it was written to protect, and a reword of either would no longer redden "
        "anything"
    )

    poisoned = tail + "\n# a mention of README" + "." + "md" + " and nothing else\n"
    assert _lane_selects(poisoned), (
        "control, and without it the assertion above is satisfied by a filter welded to "
        "False: the same call must answer True once a matching line is present"
    )
