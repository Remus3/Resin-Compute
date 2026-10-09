"""ci.yml must keep FULL history on the schedule while a history sweep ships.

WHAT THIS GUARD CLAIMS, narrow on purpose. It reads the TEXT of
`.github/workflows/ci.yml` and asserts that its `actions/checkout` step
declares a `fetch-depth` that is 0 whenever the event is the nightly
`schedule`: either a literal 0, or the one expression shape this tree ships,
`${{ (github.event_name == 'schedule' || ...) && '0' || '<N>' }}`. It CANNOT
claim the value reaches the runner - a variable, a composite action or a
`uses:` indirection would all be invisible to a line scanner - and it does
not model YAML or evaluate expressions beyond that one shape. It is a
spelling guard over one key, because the failure it prevents is an EDIT TO
THIS FILE, not a runtime behaviour.

WHY THE DEPTH IS LOAD-BEARING. `tests/test_commit_trailers.py` sweeps
`git log` and fails if any commit carries a banned agent trailer. On a
shallow clone with no range exported git answers with a truncated history,
so that sweep would pass BY CONSTRUCTION; the module detects the shallow
clone and skips instead. Since MAIN 2246 ORDER s2 (PERF-AUDIT item 10) a push
or pull-request job checks out shallow and sweeps ONLY the pushed range
(`RSC_TRAILER_RANGE`); the schedule sweeps everything at depth 0. So two
things must hold together: the schedule is full-depth, and a shallow push
checkout ships the range step. Both are pinned below.

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
DOCS_GUARDS = REPO_ROOT / ".github" / "workflows" / "docs-guards.yml"
TRAILER_SWEEP = REPO_ROOT / "tests" / "test_commit_trailers.py"

_CHECKOUT = re.compile(r"^uses:\s*actions/checkout@", re.IGNORECASE)
_FETCH_DEPTH = re.compile(r"^fetch-depth:\s*(.+?)\s*$")
#: The SHA-pinned checkout ref with its `# vX.Y.Z` tag comment.
_PINNED_CHECKOUT = re.compile(r"^uses:\s*actions/checkout@[0-9a-f]{40}\s+#\s+v\d+(?:\.\d+){0,2}$")

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


#: The one expression shape accepted for a depth that varies by event. The
#: condition must name the schedule; the fallback must be a positive depth.
_EVENT_DEPTH = re.compile(
    r"""^\$\{\{\s*\(?(?P<cond>[^&]*?)\)?\s*&&\s*'0'\s*\|\|\s*'(?P<n>\d+)'\s*\}\}$"""
)
_SCHEDULE_TERM = re.compile(r"""github\.event_name\s*==\s*'schedule'""")


def depth_is_full_on_schedule(depth: str) -> bool:
    """True for a literal 0, or for the accepted event expression that yields
    '0' when the event is the schedule."""
    if depth == "0":
        return True
    match = _EVENT_DEPTH.match(depth)
    if not match:
        return False
    cond = match.group("cond")
    if not _SCHEDULE_TERM.search(cond) or "&&" in cond or "!=" in cond or "!" in cond.replace("!=", ""):
        return False
    return int(match.group("n")) >= 1


def full_history_problems(text: str) -> list[str]:
    """Every reason `text` fails to fetch full history on the schedule.

    An empty list means all three of: at least one `actions/checkout` step was
    FOUND, every such step carries an explicit `fetch-depth`, and every value
    is 0 on the schedule. A workflow with no checkout step is a problem rather
    than a pass - that is the anti-vacuity floor, and it lives here so the
    guard below can grade census and judgement in a single assertion.
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
        elif not depth_is_full_on_schedule(step.depth):
            problems.append(
                f"line {step.line}: `{step.ref}` declares fetch-depth {step.depth!r}, which "
                f"is not 0 on the schedule - a shallow nightly sweep"
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
    "an event expression that is shallow on the schedule": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: ${{ github.event_name == 'schedule' && '1' || '0' }}
""",
    "an event expression keyed on push, not the schedule": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: ${{ github.event_name == 'push' && '0' || '100' }}
""",
    "an event expression negating the schedule": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: ${{ github.event_name != 'schedule' && '0' || '100' }}
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
    "the shipped event expression": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: ${{ (github.event_name == 'schedule' || github.event_name == 'workflow_dispatch') && '0' || '100' }}
""",
    "a schedule-only event expression without parentheses": """
jobs:
  check:
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: ${{ github.event_name == 'schedule' && '0' || '50' }}
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


def test_the_docs_lane_is_still_shallow_on_purpose():
    """THE OTHER HALF OF THE CLAIM, and it was unguarded until a refuter said so.

    `tests/test_commit_trailers.py` skips its two history arms under a shallow
    clone, and its skip reason tells a CI reader to check WHICH lane is shallow
    before changing any depth, because at least one lane here is shallow
    deliberately. That sentence is a claim about a file that module never reads.
    Nothing pinned it, so raising the docs lane to depth 0 would have made the
    reason text quietly false with no test going red - the exact stale-prose
    failure this tree keeps re-finding.

    The docs lane is depth 1 BY DESIGN: it derives its selection from
    `git ls-files`, which needs an index and not a history. So this arm asserts
    the OPPOSITE of the ci.yml arm above, and the two together are what make
    that skip reason true.

    CENSUS AND JUDGEMENT IN ONE ASSERT, same shape as the ci.yml arm: a workflow
    whose checkout step this scanner can no longer see would otherwise satisfy
    "no step declares depth 0" vacuously, forever.
    """
    steps = parse_checkout_steps(DOCS_GUARDS.read_text(encoding="utf-8"))
    problems: list[str] = []
    if not steps:
        problems.append(
            "no actions/checkout step found at all, so a rule about its depth would be "
            "a rule about nothing"
        )
    for step in steps:
        if step.depth == "0":
            problems.append(
                f"line {step.line}: `{step.ref}` now checks out FULL history. That may be "
                f"correct, but tests/test_commit_trailers.py tells a CI reader that at "
                f"least one lane is shallow deliberately - update that skip reason in the "
                f"same commit, or this tree ships prose it has stopped meaning"
            )
    assert not problems, "the docs lane changed shape: " + " | ".join(problems)


def test_the_parser_recovers_the_real_workflows_own_step():
    """Non-vacuity for the scanner against the real file, not a sample.

    The controls above are hand-typed; they prove the matcher grades text
    correctly and prove nothing about whether it can SEE ci.yml. If a future
    edit moved the checkout into a composite action the scan cannot read, the
    guard's floor would fire - but the message would blame the depth, so pin
    the shape separately for a readable next step.
    """
    steps = parse_checkout_steps(CI.read_text(encoding="utf-8"))
    # The ref is SHA-pinned with its release tag as a trailing comment (MAIN
    # ORDER 0300); tests/test_supply_chain.py owns that property. This arm
    # pins only that the scanner SEES exactly one checkout step in ci.yml, so
    # it matches the pinned shape rather than one literal SHA, and a Dependabot
    # bump does not redden a guard about history depth.
    assert len(steps) == 1 and _PINNED_CHECKOUT.match(steps[0].ref), (
        f"the scan read {[s.ref for s in steps]} out of ci.yml, which is not the single "
        f"checkout step this module was written against"
    )


# ---------------------------------------------------------------------------
# The push-job half: a shallow push checkout must ship the range sweep
# ---------------------------------------------------------------------------


def range_sweep_problems(text: str) -> list[str]:
    """Why a workflow whose checkout is shallow on push does not sweep the range.

    Executable lines only, so a comment naming the variable cannot satisfy it.
    """
    steps = parse_checkout_steps(text)
    if steps and all(step.depth == "0" for step in steps):
        return []
    executable = [
        line for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    body = "\n".join(executable)
    problems = []
    if "RSC_TRAILER_RANGE=" not in body:
        problems.append("no executable line exports RSC_TRAILER_RANGE")
    if not re.search(r"-m pytest\b[^\n]*tests/test_commit_trailers\.py", body):
        problems.append("no executable line runs tests/test_commit_trailers.py")
    return problems


def test_a_shallow_push_checkout_ships_the_range_sweep():
    """Without the range step a shallow push job enforces none of the ban:
    the sweep would skip, and the whole-history run is nightly only."""
    from tests.test_commit_trailers import TRAILER_RANGE_ENV

    assert TRAILER_RANGE_ENV == "RSC_TRAILER_RANGE", (
        "the trailer module renamed its range variable; re-point this guard"
    )
    problems = range_sweep_problems(CI.read_text(encoding="utf-8"))
    assert not problems, "ci.yml checks out shallow on push but: " + " | ".join(problems)


def test_the_range_detector_fires_and_spares():
    """Non-vacuity in both directions over hand-typed workflow text."""
    shallow = (
        "      - uses: actions/checkout@v6\n"
        "        with:\n"
        "          fetch-depth: ${{ github.event_name == 'schedule' && '0' || '100' }}\n"
    )
    assert range_sweep_problems(shallow), "a shallow push with no range step passed"
    commented = shallow + (
        "          # export RSC_TRAILER_RANGE=x; python -m pytest tests/test_commit_trailers.py\n"
    )
    assert range_sweep_problems(commented), "a comment satisfied the range detector"
    shipped = shallow + (
        '            *[!0]*) export RSC_TRAILER_RANGE="${base}..HEAD" ;;\n'
        "          python -m pytest -rs tests/test_commit_trailers.py\n"
    )
    assert not range_sweep_problems(shipped)
    full = "      - uses: actions/checkout@v6\n        with:\n          fetch-depth: 0\n"
    assert not range_sweep_problems(full), "a full-depth checkout needs no range step"
