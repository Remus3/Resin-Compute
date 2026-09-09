"""ci.yml must not return to a shallow checkout while a history sweep ships.

WHAT THIS GUARD CLAIMS, narrow on purpose. It reads the TEXT of
`.github/workflows/ci.yml` and asserts that its `actions/checkout` step
declares `fetch-depth: 0`. That is the whole claim. It CANNOT claim the flag
reaches the runner - a variable, a composite action, a reusable workflow or a
`uses:` indirection would all be invisible to a line scanner - and it does not
model YAML. It is a spelling guard over one key, which is the right instrument
here because the failure it prevents is an EDIT TO THIS FILE, not a runtime
behaviour.

WHY THE DEPTH IS LOAD-BEARING. `tests/test_commit_trailers.py` sweeps
`git log` over the whole history and fails if any commit carries a banned
agent trailer. On a depth-1 clone git answers with one commit rather than
erroring, so that sweep would pass BY CONSTRUCTION; the module detects the
shallow clone and skips instead, with a reason naming this very flag. Honest,
and it left CI enforcing none of a rule CLAUDE.md states as hard. Depth 0 is
what makes those arms run on the runner.

TIED TO ITS PREMISE, as its own arm. If that sweep ever stops reading history,
this guard becomes a rule about nothing while still LOOKING like protection,
and the correct response is to delete it rather than leave it standing. Same
shape as
`test_pytest_ini_does_not_itself_supply_the_skip_reporting_the_workflow_adds`
in tests/test_ci_workflow_complement.py.

CENSUS AND JUDGEMENT IN ONE ASSERT. "The checkout is not shallow" is trivially
true of a file with no checkout step at all, and of one whose step the scanner
can no longer see. A floor kept in a separate arm leaves the primary arm
vacuous in the window where the floor is red, so `full_history_problems()`
reports "no checkout step found" as a PROBLEM and the guard grades one list.

NO YAML LIBRARY. PyYAML is installed on the author's box and is NOT in
requirements-dev.txt, which pins ruff, pytest and mypy only. A guard importing
it would pass here and fail on the runner, which is the reverse of useful.

NO GIT, EITHER. Nothing in this module shells out, so an exported GIT_DIR, a
linked worktree or a Download-ZIP copy cannot change any verdict, and no arm
here skips for any reason.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
TRAILER_SWEEP = REPO_ROOT / "tests" / "test_commit_trailers.py"

_CHECKOUT = re.compile(r"^uses:\s*actions/checkout@", re.IGNORECASE)
_FETCH_DEPTH = re.compile(r"^fetch-depth:\s*(\S+)")

#: A call whose FIRST argument is the literal `log`, in either shape this tree
#: could plausibly use: a helper (`_git("log", ...)`) or an argv list
#: (`["git", "log", ...]`). Anchored on the CALL, not on the words, because
#: `git log` appears in prose in that module's own docstring and in this one -
#: an unanchored match would be satisfied by the prose alone and would survive
#: the deletion of every actual sweep.
_GIT_LOG_CALL = re.compile(r"""\(\s*["']log["']\s*[,)]|["']git["']\s*,\s*["']log["']""")


@dataclass(frozen=True)
class CheckoutStep:
    """One `actions/checkout` step as the line scanner sees it.

    `depth` is None when the step declares no `fetch-depth` key at all. That is
    NOT the same as unknown: the action's documented default is 1, so an absent
    key is a shallow clone and is graded as one.
    """

    ref: str
    depth: str | None
    line: int


def parse_checkout_steps(text: str) -> list[CheckoutStep]:
    """Every `actions/checkout` list item, with the fetch-depth it declares.

    A step is a `- ` list item; its body runs until the first non-blank,
    non-comment line indented no further than the `- ` itself, which is the
    next step or the end of the block. Comment lines are skipped, so a
    `# fetch-depth: 0` in the prose above a shallow value does not flip the
    verdict - a control below plants exactly that.
    """
    steps: list[CheckoutStep] = []
    lines = text.splitlines()
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped.startswith("- "):
            continue
        body = stripped[2:].strip()
        if not _CHECKOUT.match(body):
            continue
        item_indent = len(raw) - len(raw.lstrip())
        depth: str | None = None
        for follower in lines[index + 1:]:
            bare = follower.strip()
            if not bare or bare.startswith("#"):
                continue
            if len(follower) - len(follower.lstrip()) <= item_indent:
                break
            match = _FETCH_DEPTH.match(bare)
            if match:
                depth = match.group(1).strip().strip("'\"")
                break
        steps.append(CheckoutStep(ref=body, depth=depth, line=index + 1))
    return steps


def full_history_problems(text: str) -> list[str]:
    """Every reason `text` fails to declare a full-history checkout.

    An empty list means all three of: at least one `actions/checkout` step was
    FOUND, every such step carries an explicit `fetch-depth`, and every value
    is 0. A workflow with no checkout step is a problem rather than a pass -
    that is the anti-vacuity floor, and it lives here so the guard below can
    grade census and judgement in a single assertion.
    """
    steps = parse_checkout_steps(text)
    problems: list[str] = []
    if not steps:
        problems.append(
            "no actions/checkout step found at all - either the checkout moved into a "
            "shape this line scanner cannot read, or it is gone; grading a shallow "
            "depth against zero steps would pass forever"
        )
    for step in steps:
        if step.depth is None:
            problems.append(
                f"line {step.line}: `{step.ref}` declares no fetch-depth key, and the "
                f"action defaults to 1 - a shallow clone"
            )
        elif step.depth != "0":
            problems.append(
                f"line {step.line}: `{step.ref}` declares fetch-depth {step.depth!r} - "
                f"a shallow clone"
            )
    return problems


# ---------------------------------------------------------------------------
# The premise. Without it this whole module is a rule about nothing.
# ---------------------------------------------------------------------------


def test_the_sweep_this_depth_exists_for_still_reads_history():
    """PREMISE, as its own arm.

    `fetch-depth: 0` is only worth guarding while something in the suite
    actually reads history. If tests/test_commit_trailers.py stops doing so,
    the right move is to DELETE the guard below and drop the workflow back to a
    depth-1 clone, not to keep paying for a fetch nothing consumes while a
    green tick suggests a policy is enforced.
    """
    assert TRAILER_SWEEP.is_file(), (
        f"{TRAILER_SWEEP} is gone. It was the only reason ci.yml fetches full history; "
        f"either re-point this module at whatever replaced it, or delete this module and "
        f"restore fetch-depth: 1"
    )
    text = TRAILER_SWEEP.read_text(encoding="utf-8")
    assert _GIT_LOG_CALL.search(text), (
        f"{TRAILER_SWEEP.name} no longer invokes `git log` in any shape this scan can "
        f"read. If it truly stopped sweeping history, the fetch-depth guard below is "
        f"guarding nothing and should be deleted rather than left looking like "
        f"protection; re-read both files before changing either"
    )


def test_the_history_call_detector_reads_calls_and_not_prose():
    """Non-vacuity for the premise detector, in both directions."""
    assert _GIT_LOG_CALL.search('raw = _git("log", "--format=%H")')
    assert _GIT_LOG_CALL.search("out = _git('log')")
    assert _GIT_LOG_CALL.search('subprocess.run(["git", "log", "-n", "1"])')
    assert not _GIT_LOG_CALL.search("a guard that runs `git log` over the past")
    assert not _GIT_LOG_CALL.search('_git("rev-parse", "--is-shallow-repository")')


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_the_ci_workflow_is_where_this_module_expects_it():
    """A missing file would raise FileNotFoundError inside the guard below,
    which reads as a broken test rather than as the real finding."""
    assert CI.is_file(), f"{CI} is missing"


def test_the_ci_checkout_still_asks_for_full_history():
    """THE GUARD, with its anti-vacuity floor inside the same assertion.

    Reports every offending step at once rather than the first, so a future
    workflow with two checkouts does not need two red runs to fix.
    """
    problems = full_history_problems(CI.read_text(encoding="utf-8"))
    assert not problems, (
        "ci.yml no longer checks out full history, so the `git log` trailer sweep in "
        "tests/test_commit_trailers.py will SKIP on the runner and CI will enforce none "
        "of the Co-Authored-By ban: " + " | ".join(problems)
    )


# ---------------------------------------------------------------------------
# Positive control, both directions, over hand-typed yaml-shaped text
# ---------------------------------------------------------------------------

#: Shapes that MUST be flagged. Varied on purpose: a detector tested only
#: against the one spelling its author had in mind cannot discover that it is
#: narrow.
_FLAGGED: dict[str, str] = {
    "unquoted depth 1": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 1
""",
    "single-quoted depth 1": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: '1'
""",
    "double-quoted depth 20": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: "20"
""",
    "no fetch-depth key at all": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.11'
""",
    "depth 0 only in a comment": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          # raise this to 0 the day a guard reads history
          fetch-depth: 1
""",
    "no checkout step at all": """
jobs:
  check:
    steps:
      - uses: actions/setup-python@v6
        with:
          fetch-depth: 0
""",
    "one full checkout and one shallow": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - uses: actions/checkout@v6
        with:
          path: other
          fetch-depth: 1
""",
}

#: Shapes that MUST survive. A control that only rejects passes for a detector
#: welded to True, exactly as a control that only accepts passes for one welded
#: to False.
_CLEARED: dict[str, str] = {
    "unquoted depth 0": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
""",
    "single-quoted depth 0": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: '0'
""",
    "double-quoted depth 0": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: "0"
""",
    "two-space list indentation": """
jobs:
  check:
    steps:
    - uses: actions/checkout@v6
      with:
        fetch-depth: 0
""",
    "list items flush left": """
steps:
- uses: actions/checkout@v6
  with:
    fetch-depth: 0
""",
    "a pinned sha rather than a tag": """
jobs:
  check:
    steps:
      - uses: actions/checkout@0ad4b8fadaa221de15dcec353f45205ec38ea70b
        with:
          fetch-depth: 0
""",
    "comments and blanks between the key and the step": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:

          # A long comment block, as the real file carries.
          #
          # Mentioning fetch-depth: 1 in prose, which must not be read.
          fetch-depth: 0
""",
    "a later step whose shallow depth is not a checkout": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - uses: some/other-action@v1
        with:
          fetch-depth: 1
""",
}


def test_the_matcher_flags_every_shallow_shape_and_clears_every_full_one():
    """BOTH DIRECTIONS IN ONE ASSERT.

    A reject-only control passes for a detector welded to True; an
    accept-only control passes for one welded to False. Graded together, and
    through the SAME `full_history_problems()` the guard above calls, so this
    is a statement about the shipped code path rather than about a parallel
    copy of it.
    """
    silent = [name for name, text in _FLAGGED.items() if not full_history_problems(text)]
    noisy = {
        name: full_history_problems(text)
        for name, text in _CLEARED.items()
        if full_history_problems(text)
    }
    assert not silent and not noisy, (
        f"the fetch-depth matcher is not reading what it claims to read. Shallow shapes "
        f"it failed to flag: {silent or 'none'}. Full-history shapes it wrongly flagged: "
        f"{noisy or 'none'}"
    )


def test_the_parser_recovers_the_real_workflows_own_step():
    """Non-vacuity for the scanner against the real file, not a sample.

    The controls above are hand-typed; they prove the matcher grades text
    correctly and prove nothing about whether it can SEE ci.yml. If a future
    edit moved the checkout into a composite action the scan cannot read, the
    guard's floor would fire - but the message would blame the depth, so pin
    the shape separately for a readable next step.
    """
    steps = parse_checkout_steps(CI.read_text(encoding="utf-8"))
    assert [s.ref for s in steps] == ["uses: actions/checkout@v6"], (
        f"the scan read {[s.ref for s in steps]} out of ci.yml, which is not the single "
        f"checkout step this module was written against"
    )
