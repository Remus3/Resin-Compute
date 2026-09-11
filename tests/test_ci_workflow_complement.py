"""The two CI workflows must COVER every push between them, with no hole.

`ci.yml` carries `paths-ignore: ['**/*.md']` and `docs-guards.yml` carries the
matching `paths: ['**/*.md']`. That pairing is what makes a docs-only push cheap
without making it unverified: `ci` declines it and `docs-guards` picks it up.

THE FAILURE THIS GUARDS IS A COVERAGE HOLE, NOT A RED BUILD. Add a second entry
to `ci.yml`'s `paths-ignore` - say `'docs/**'` - and forget the matching `paths`
entry in `docs-guards.yml`, and pushes touching that path fire NEITHER workflow.
Nothing goes red. Nothing warns. The tree simply stops being checked for a whole
class of file, and the only evidence is an absence of runs that nobody is
looking for.

`ci.yml` already carries a COMMENT instructing the author to add the matching
entry in the same commit. An instruction is not a guard: it is read only by
someone who already opened the right file. Sibling-C enforces this
mechanically in CI (its "docs-guard complement is wired" step); this tree had
the comment and no enforcement until now.

Parsed with a line scanner rather than a YAML library because this repository is
stdlib-only at runtime and PyYAML is not a dependency. The scan is deliberately
narrow - it reads the two `on:` trigger blocks and nothing else.

WHICH GIT GATE THIS MODULE USES, AND WHY THAT ONE.

`require_git_repository()` - the RUN-time per-test shape.

Not `skip_module_without_git()`. Nothing at module scope reaches git: every
workflow-parsing arm reads `.github/workflows/*.yml` off disk, and those are
present in a `git archive` extract exactly as they are in a clone. Measured
under the absence mechanism in `tests/test_conftest_git_gate_sites.py`: 5 of 34
nodes reach git, so 29 keep running. An import-time whole-module skip would
delete the coverage-hole guard this file exists for on a checkout where it is
still perfectly answerable.

THE GATE IS CALLED AT FOUR PLACES, BECAUSE GIT IS REACHED BY FOUR ROUTES AND
THREE OF THEM ARE NOT `_git_z`. Gating only the obvious helper would have left
three of the five nodes failing, which is how a partial gate reads as a
finished one:

  1. `_git_z()` - shells `git` directly.
  2. `_listed()` - shells `tools/precommit_gate.py --list-tracked`, which builds
     its own corpus from git INSIDE the child process. The failure therefore
     surfaces as a non-zero child exit rather than as an OSError here, so it
     looks nothing like case 1 at the call site.
  3. `test_no_exempt_prefix_names_a_path_that_can_actually_be_committed` - an
     inline `git check-ignore` in the test body.
  4. `test_the_gitignore_probe_actually_distinguishes_ignored_from_tracked` -
     the non-vacuity partner of 3, with its own inline `git check-ignore`.

Cases 3 and 4 are gated in their bodies rather than through a shared helper
because there is no shared helper to gate: each builds its own `subprocess.run`.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

CI = WORKFLOWS / "ci.yml"
DOCS_GUARDS = WORKFLOWS / "docs-guards.yml"

TOOLS = REPO_ROOT / "tools"
GATE = TOOLS / "precommit_gate.py"
PYTEST_INI = REPO_ROOT / "pytest.ini"


def _trigger_patterns(path: Path, key: str) -> set[str]:
    """Every glob listed under `key:` inside the workflow's `on:` block.

    Stops at the first line that is neither a list item nor a comment nor
    blank, so a `paths-ignore:` under `push:` and another under
    `pull_request:` are both collected while the rest of the file is ignored.
    """
    found: set[str] = set()
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, raw in enumerate(lines):
        if raw.strip() != f"{key}:":
            continue
        for follower in lines[index + 1:]:
            stripped = follower.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not stripped.startswith("- "):
                break
            found.add(stripped[2:].strip().strip("'\""))
    return found


def test_both_workflow_files_exist():
    """The complement is meaningless if one half has been renamed away."""
    assert CI.is_file(), f"{CI} is missing"
    assert DOCS_GUARDS.is_file(), f"{DOCS_GUARDS} is missing"


def test_the_parser_actually_recovers_the_known_pairing():
    """Non-vacuity. A parser that silently found nothing would pass everything
    below it forever, which is the same class of bug the pairing itself guards."""
    ignored = _trigger_patterns(CI, "paths-ignore")
    covered = _trigger_patterns(DOCS_GUARDS, "paths")
    assert "**/*.md" in ignored, f"ci.yml paths-ignore parsed as {ignored}"
    assert "**/*.md" in covered, f"docs-guards.yml paths parsed as {covered}"


def test_every_path_ci_ignores_is_covered_by_docs_guards():
    """THE GUARD. A pattern in neither workflow is a class of file nobody checks."""
    ignored = _trigger_patterns(CI, "paths-ignore")
    covered = _trigger_patterns(DOCS_GUARDS, "paths")
    uncovered = sorted(ignored - covered)
    assert not uncovered, (
        f"ci.yml declines {uncovered} and docs-guards.yml does not pick them up, so a "
        f"push touching those paths fires NEITHER workflow and is never checked. This "
        f"does not go red on its own - it goes SILENT. Add the matching entry to "
        f"{DOCS_GUARDS.name}'s `paths:` in the same commit, as ci.yml's own comment says."
    )


@pytest.mark.parametrize("mechanism", ["docs-guards.yml", "precommit_gate.py"])
def test_docs_guards_reruns_itself_when_its_own_mechanism_changes(mechanism: str):
    """An edit to the checker must re-run the checker.

    Otherwise a change that breaks the banned-glyph engine lands green, because
    the only workflow that exercises it was not triggered by the file that
    changed it.
    """
    covered = _trigger_patterns(DOCS_GUARDS, "paths")
    assert any(mechanism in pattern for pattern in covered), (
        f"docs-guards.yml does not re-run itself when {mechanism} changes; "
        f"its paths are {sorted(covered)}"
    )


def test_ci_still_ignores_markdown_so_the_complement_is_load_bearing():
    """If ci.yml stopped ignoring .md this whole file would be guarding nothing.

    Stated as its own arm so that the day someone deletes the `paths-ignore`,
    this fails loudly and points at the four tests above rather than leaving
    them quietly tautological.
    """
    assert "**/*.md" in _trigger_patterns(CI, "paths-ignore"), (
        "ci.yml no longer ignores markdown. That may be correct, but the "
        "ci/docs-guards complement this module guards no longer exists - "
        "re-read whether docs-guards.yml is still needed at all."
    )


def test_the_scanner_ignores_keys_outside_the_trigger_block():
    """The `paths` word appears in prose and in step bodies; only triggers count."""
    assert not any(
        pattern.startswith("name:") or pattern.endswith(":")
        for pattern in _trigger_patterns(DOCS_GUARDS, "paths")
    )


# ---------------------------------------------------------------------------
# THE SECOND HALF OF THE RULE: SELECTION.
#
# Everything above guards the TRIGGER complement - which pushes fire which
# workflow. It held under attack and is unchanged. What it never covered is
# what each workflow does once it fires, and on 2026-09-06 an adversarial pass
# found four defects living in exactly that blind spot:
#
#   1. Both ASCII steps handed their path list over with
#      `xargs -r -a list.txt`. That splits on WHITESPACE, so a tracked path
#      containing a space became two arguments that both failed to open; the
#      gate warned on stderr, continued, and printed "7-bit ASCII clean" with
#      EXIT 0 over a file carrying an em-dash. A single quote failed the other
#      way - unmatched quote, red on a legal Linux filename.
#   2. ci.yml selected by an extension ALLOWLIST and docs-guards.yml selected
#      markdown. 14 tracked files matched neither, among them every .githooks/
#      script and ops/install_scheduled_task.ps1 - the file class the whole
#      7-bit-ASCII rule exists for.
#   3. docs-guards.yml collected both test suites into ONE root-level pytest.
#   4. It also passed -q on top of pytest.ini's own, doubling to -qq and
#      suppressing the summary line from the only step that runs assertions.
#
# All four are the same shape as the trigger hole: nothing goes red, the tree
# just quietly stops being checked. Once this repository is public the shape
# gets worse, because a fork's pull request has never run
# scripts/install_hooks.py - for that contributor CI is not the backstop, it is
# the only gate there is.
# ---------------------------------------------------------------------------


def _executable_lines(path: Path) -> list[str]:
    """Workflow lines that actually RUN, with comments dropped.

    A line whose first non-space character is `#` is either a YAML comment or a
    shell comment inside a `run: |` block; neither executes. Dropping them
    matters here because the comments in both workflows now DISCUSS the removed
    constructs at length, and a naive substring scan over the whole file would
    be answered by the prose warning against the very thing it checks for.
    """
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def _gate(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GATE), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        timeout=180,
    )


def _git_z(*args: str) -> list[str]:
    """NUL-delimited git output.

    Deliberately NOT routed through the gate: this is the independent side of
    the cross-checks below, so it must not share the gate's implementation.

    "The gate" in that sentence is `tools/precommit_gate.py`, not the git gate
    added below - they are unrelated mechanisms that unluckily share the word.
    `require_git_repository()` here converts an unreachable git into a SKIP with
    a reason, instead of the FileNotFoundError the bare `subprocess.run` raises.
    """
    require_git_repository()
    out = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        timeout=120,
    )
    assert out.returncode == 0, f"git {' '.join(args)} failed: {out.stderr!r}"
    return [p for p in out.stdout.decode("utf-8", "surrogateescape").split("\0") if p]


def _listed(mode: str) -> set[str]:
    """The gate's own tracked-file corpus, for `mode` in ("source", "docs").

    GATED TOO, and this is the route a reader is most likely to miss.
    `tools/precommit_gate.py --list-tracked` builds its corpus from git inside
    the CHILD process, so with git unreachable the child exits non-zero and the
    assertion below fails on an unhelpful stderr - a FAILURE, not a skip, and
    with no OSError anywhere near this frame to hint at the cause.
    """
    require_git_repository()
    out = _gate("--list-tracked", mode)
    assert out.returncode == 0, f"--list-tracked {mode} failed: {out.stderr!r}"
    return {p for p in out.stdout.decode("utf-8", "surrogateescape").split("\0") if p}


# --- Defect 2: the two gates must PARTITION the tracked set ----------------


def test_the_two_ascii_gates_cover_every_tracked_file_between_them():
    """THE COVERAGE GUARD. A tracked file in neither half is never scanned.

    This is the selection-side twin of the trigger guard above, and it fails
    the same way: silently. Nothing goes red when a file class stops being
    covered - there is simply no run that ever looked at it.
    """
    tracked = set(_git_z("ls-files", "-z"))
    source = _listed("source")
    docs = _listed("docs")
    uncovered = sorted(tracked - (source | docs))
    assert not uncovered, (
        f"{len(uncovered)} tracked file(s) are scanned by NEITHER ASCII gate: {uncovered}"
    )
    overlap = sorted(source & docs)
    assert not overlap, f"both gates claim {overlap}; the halves must be disjoint"
    assert source | docs == tracked, "the two halves do not reconstruct the tracked set"


def test_the_partition_reaches_the_files_the_old_allowlist_missed():
    """Named regression over real paths from the measured uncovered set.

    ops/install_scheduled_task.ps1 is the sting: it carries its own 17-line
    ASCII-ONLY header citing the PowerShell 5.1 parse failure, and it is the
    file class the rule exists for. CI did not scan it.
    """
    source = _listed("source")
    for path in (
        "ops/install_scheduled_task.ps1",
        ".githooks/pre-commit",
        ".githooks/commit-msg",
        ".githooks/pre-push",
        ".gitattributes",
        "LICENSE",
        "NOTICE",
        "requirements.txt",
    ):
        assert (REPO_ROOT / path).is_file(), f"{path} is not on disk - fix this test, not the gate"
        assert path in source, f"{path} is tracked but no ASCII gate selects it"


def test_the_old_extension_allowlist_really_would_have_missed_them():
    """NON-VACUITY for the arm above.

    If the discarded allowlist had covered those paths anyway, the test above
    would be asserting nothing. Reconstructed verbatim from the ci.yml step as
    it stood at commit 41e7184.
    """
    old_allowlist = (".py", ".toml", ".ini", ".yml", ".yaml", ".json", ".js", ".sh")
    probes = (
        "ops/install_scheduled_task.ps1",
        ".githooks/pre-commit",
        "LICENSE",
        "requirements.txt",
    )
    missed = [p for p in probes if not p.endswith(old_allowlist)]
    assert len(missed) == len(probes), (
        f"the old allowlist would have covered {set(probes) - set(missed)} after all; "
        f"the regression test above is weaker than it reads"
    )


def test_no_exempt_prefix_names_a_path_that_can_actually_be_committed():
    """ROOT CAUSE, not just the one instance.

    `data/external/` sat in the gate's exemption tuple while being gitignored
    NOWHERE and referenced by NO other file in the tree - so the one gate that
    would flag a FETCHED upstream payload was switched off in advance at a path
    `git add -A` would have staged without a word. Upstream character names
    carry non-ASCII codepoints, and the vendoring refusal in
    docs/LICENSE_NOTES.md is the single leg the publication decision rests on.

    The fix is not "delete that one string". It is that an exemption for a
    committable path is a pre-cut hole, so every prefix must be gitignored.

    Gated in the body: the `git check-ignore` below is built here rather than in
    a shared helper, so there is nothing else to attach the gate to.
    """
    require_git_repository()
    sys.path.insert(0, str(TOOLS))
    try:
        import precommit_gate
    finally:
        sys.path.pop(0)

    for prefix in precommit_gate._ASCII_EXEMPT_PREFIXES:
        probe = f"{prefix}probe.json"
        checked = subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", probe],
            cwd=str(REPO_ROOT),
            capture_output=True,
            timeout=60,
        )
        assert checked.returncode == 0, (
            f"the ASCII gate exempts {prefix!r}, but git does NOT ignore {probe} - "
            f"so a file there can be committed AND is never scanned. Either ignore "
            f"the path or drop the exemption."
        )


def test_the_gitignore_probe_actually_distinguishes_ignored_from_tracked():
    """NON-VACUITY for the arm above: the probe must reject a committable path.

    Gated in the body for the same reason as its partner, and it MUST carry its
    own gate. If only the arm above were gated, this one would still fail with
    git unreachable - and a non-vacuity partner that fails while the arm it
    defends skips is the worst of the three possible states.
    """
    require_git_repository()
    checked = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", "core/probe_not_ignored.json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        timeout=60,
    )
    assert checked.returncode != 0, (
        "git check-ignore claims core/ is ignored, so the exemption guard above "
        "would pass for any prefix at all"
    )


# --- Defect 1: no whitespace-splitting handoff anywhere --------------------


def test_no_workflow_hands_a_path_list_to_a_whitespace_splitting_xargs():
    """REGRESSION. Argument splitting on whitespace honours quotes too.

    Measured against the shipped step: one path containing a space produced
    EXIT 0 and "7-bit ASCII clean" over a planted em-dash, while the same file
    passed directly produced EXIT 1. README.md advertises a space-containing
    install path as a deliberately exercised case; these two steps were the
    pair that had not been hardened for it.
    """
    for workflow in (CI, DOCS_GUARDS):
        for line in _executable_lines(workflow):
            if "xargs" not in line:
                continue
            assert "-0" in line.split(), (
                f"{workflow.name} runs `{line}` without -0, so the list is split on "
                f"whitespace and a path containing a space is silently skipped while "
                f"the step still exits 0"
            )


def test_the_splitting_detector_fires_on_the_shipped_form():
    """NON-VACUITY: the detector's predicate must reject the exact shipped line."""
    shipped = "xargs -r -a src_files.txt python tools/precommit_gate.py --scan-files"
    assert "xargs" in shipped
    assert "-0" not in shipped.split(), (
        "the detector's own predicate would have passed the defective line"
    )


def test_the_comment_prose_is_not_what_the_detector_reads():
    """NON-VACUITY, second arm. Both workflows now DISCUSS the removed construct.

    If `_executable_lines` stopped dropping comments, the guard above would be
    reading the prose that explains the fix instead of the code that applies
    it - and would go red on a correct file, which teaches people to delete it.
    """
    for workflow in (CI, DOCS_GUARDS):
        raw = workflow.read_text(encoding="utf-8")
        assert "xargs" in raw, f"{workflow.name} no longer mentions it; re-read this guard"
        assert not any("xargs" in line for line in _executable_lines(workflow)), (
            f"{workflow.name} names it on an EXECUTABLE line; the guard above is doing "
            f"real work rather than being satisfied by prose alone"
        )


# --- Defect 3: the two suites are never collected together -----------------


def test_docs_guards_never_hands_one_pytest_both_suites():
    """pytest.ini and CLAUDE.md both forbid a root-level dual collection.

    docs-guards.yml selected the engine's tests alongside the application's
    into ONE list and ran the lot in a single invocation. It had been green on
    every docs push since it was written, which is exactly why nobody noticed -
    a rule broken inside a passing job stays broken.
    """
    lines = _executable_lines(DOCS_GUARDS)
    body = "\n".join(lines)
    assert "app_guards.z" in body, "docs-guards.yml has no application-suite bucket"
    assert "engine_guards.z" in body, "docs-guards.yml has no engine-suite bucket"

    mixed = [ln for ln in lines if "app_guards" in ln and "engine_guards" in ln]
    assert not mixed, f"one line handles both buckets, so they can still be merged: {mixed}"

    invocations = [ln for ln in lines if "-m pytest" in ln]
    assert len(invocations) >= 2, (
        f"docs-guards.yml runs pytest {len(invocations)} time(s); the two suites need "
        f"one invocation each. Lines: {invocations}"
    )
    for line in invocations:
        assert not ("app[@]" in line and "engine[@]" in line), (
            f"one pytest invocation covers both suites: {line}"
        )


def test_no_workflow_writes_its_intermediates_into_the_checkout():
    """Found by this module's own surviving-neighbour arm, 2026-09-06.

    docs-guards.yml dropped its selection lists into the repo ROOT. The old
    ones were .txt, so a hand-run left junk that the next `git add -A` would
    stage and the ASCII gate would wave through as valid text. The rewritten
    ones are NUL-delimited, so the same accident is caught - but loudly failing
    on a file that should never have been there is not the fix, and .gitignore
    is not the fix either. The fix is to write outside the checkout.

    Measured: with the lists in the repo root, staging them made the ci.yml
    ASCII sweep report three BINARY findings and exit 1 on an otherwise clean
    tree.
    """
    for workflow in (CI, DOCS_GUARDS):
        for line in _executable_lines(workflow):
            if ">" not in line and ">>" not in line:
                continue
            # Redirections into a bare relative name land in the checkout.
            for token in line.split():
                if not token.startswith(("app_guards", "engine_guards", "candidate_", "unbucketed", "md_guards", "src_files", "md_files")):
                    continue
                raise AssertionError(
                    f"{workflow.name} redirects into {token!r} in the checkout: `{line}`. "
                    f"Write it under \"${{RUNNER_TEMP:-/tmp}}\" instead - anything left in "
                    f"the repo root is staged by the next `git add -A`."
                )


def test_the_intermediate_detector_fires_on_the_shipped_form():
    """NON-VACUITY: the exact shipped redirection must be rejected."""
    shipped = "git ls-files '*.py' > src_files.txt"
    offenders = [
        t for t in shipped.split()
        if t.startswith(("app_guards", "engine_guards", "candidate_", "unbucketed", "md_guards", "src_files", "md_files"))
    ]
    assert offenders == ["src_files.txt"], (
        f"the detector's predicate would have passed the shipped line: {offenders}"
    )


def test_the_suite_split_is_load_bearing_and_not_decoration():
    """The derived guard set must actually span both suites TODAY.

    Otherwise the split above is a no-op that would keep passing after someone
    reintroduced the merged invocation. Re-derives the selection with the same
    pathspec and the same regex the workflow uses.
    """
    candidates = _git_z("ls-files", "-z", "*/tests/*.py", "tests/*.py")
    pattern = re.compile(r"\.md([^a-zA-Z0-9]|$)")
    selected = [
        p for p in candidates
        if pattern.search((REPO_ROOT / p).read_text(encoding="utf-8", errors="replace"))
    ]
    engine = {p for p in selected if p.startswith("agents/pity_engine/tests/")}
    app = {p for p in selected if p.startswith("tests/")}
    assert engine, (
        "no engine test reads tracked .md any more, so the suite split in "
        "docs-guards.yml is currently vacuous - still correct to keep, but this arm "
        "no longer proves it works. Re-read the workflow before trusting it."
    )
    assert app, "no application test reads tracked .md; docs-guards.yml would run nothing"
    assert not engine & app, "a path landed in both buckets"
    assert engine | app == set(selected), (
        f"selected guards fall outside both buckets and would be dropped: "
        f"{sorted(set(selected) - engine - app)}"
    )


# --- Defect 4: no doubled -q ----------------------------------------------


def test_pytest_ini_still_carries_the_q_that_makes_a_second_one_harmful():
    """PREMISE, stated as its own arm.

    The guard below is only meaningful while pytest.ini supplies -q. If that
    line is ever dropped, the guard becomes a rule about nothing rather than
    silently continuing to look like protection.
    """
    addopts = [
        ln for ln in PYTEST_INI.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("addopts")
    ]
    assert addopts, "pytest.ini has no addopts line"
    assert any("-q" in ln for ln in addopts), f"pytest.ini addopts no longer carries -q: {addopts}"


def test_no_workflow_doubles_pytest_quiet_into_qq():
    """A second -q makes it -qq, which SUPPRESSES the summary line.

    docs-guards.yml passed one on the single step in the whole job that runs
    assertions, so its log was a wall of dots and no count. This tree records
    that trap in its own conventions; it was live in a workflow.
    """
    for workflow in (CI, DOCS_GUARDS):
        for line in _executable_lines(workflow):
            if "-m pytest" not in line:
                continue
            tokens = line.split()
            assert "-q" not in tokens and "-qq" not in tokens, (
                f"{workflow.name} runs `{line}`; pytest.ini already sets -q, so this "
                f"doubles to -qq and the summary count disappears"
            )


def test_the_quiet_detector_fires_on_the_shipped_form():
    """NON-VACUITY: the exact line that was shipped must be rejected."""
    shipped = "xargs -r -a md_guards.txt python -m pytest -q --tb=short"
    assert "-m pytest" in shipped
    assert "-q" in shipped.split(), "the detector's predicate would have passed the shipped line"


# --- The gate itself: fail CLOSED, and legitimate neighbours survive -------


def test_the_scan_mode_refuses_to_report_clean_over_zero_files():
    """The vacuous pass, closed at the engine rather than at one caller.

    Before the fix, `--scan-files` with nothing readable printed
    "0 file(s) scanned, 7-bit ASCII clean" and returned 0.
    """
    out = _gate("--scan-files")
    assert out.returncode == 1, f"selecting nothing exited {out.returncode}, expected 1"


def test_the_scan_mode_refuses_a_path_it_cannot_read():
    """An unreadable named path is a finding, not a warning.

    The caller NAMED the file; being unable to open it means the sweep did not
    cover what it was asked to cover, which is indistinguishable from clean
    unless it is reported.
    """
    out = _gate("--scan-files", "no_such_file_zz9.py")
    assert out.returncode == 1, f"an unreadable path exited {out.returncode}, expected 1"
    assert b"UNREADABLE" in out.stderr, out.stderr


def test_the_scan_mode_still_passes_a_clean_tracked_file():
    """THE SURVIVING-NEIGHBOUR ARM.

    A sweep that scored full marks by refusing everything would satisfy both
    arms above. This one fails if the gate became a blanket refusal.
    """
    out = _gate("--scan-files", "pytest.ini")
    assert out.returncode == 0, f"a clean tracked file exited {out.returncode}: {out.stderr!r}"
    assert b"7-bit ASCII clean" in out.stdout, out.stdout


def test_the_expect_count_cross_check_rejects_a_short_list():
    """The anti-vacuity arm the workflows now rely on.

    `test -s src_files.txt` only ever asserted the LIST was non-empty, never
    that anything was SCANNED - which is why the splitting defect sailed past
    it.
    """
    ok = _gate("--expect-count", "1", "--scan-files", "pytest.ini")
    assert ok.returncode == 0, f"a matching count was rejected: {ok.stderr!r}"
    bad = _gate("--expect-count", "99", "--scan-files", "pytest.ini")
    assert bad.returncode == 1, f"a mismatched count exited {bad.returncode}, expected 1"


def test_both_workflows_cross_check_the_count_they_sweep():
    """Neither ASCII step may go back to asserting only that a list is non-empty."""
    for workflow in (CI, DOCS_GUARDS):
        body = "\n".join(_executable_lines(workflow))
        assert "--expect-count" in body, (
            f"{workflow.name} sweeps without an --expect-count cross-check, so a "
            f"mangled or truncated path list would pass as clean"
        )


# ---------------------------------------------------------------------------
# THE FIFTH DEFECT CLASS: A SUITE THAT RUNS IN CI AND WILL NOT SAY WHAT IT
# DECLINED TO RUN.
#
# Everything above guards the TRIGGER complement and the SELECTION each
# workflow makes once it fires. Neither says anything about what the log READS
# LIKE afterwards, and on 2026-09-09 that blind spot was measured on GitHub run
# 34343895319 (ubuntu-latest, Python 3.11.16):
#
#     1 failed, 1636 passed, 19 skipped in 24.30s
#
# NINETEEN SKIPS AND NOT ONE OF THEM NAMED. The same tree on the author's
# Windows box reports 1, so eighteen arms silently do not run on the machine
# that actually decides red, and nothing in the log says which or why.
#
# THIS IS THE SAME SHAPE AS THE FOUR DEFECTS ABOVE: nothing goes red, the tree
# just quietly stops being checked. A skip that names no reason is
# indistinguishable from a test that was never written, and this tree's
# three-disposition doctrine turns on exactly that text - ran-and-found-nothing
# and not-present-at-all are BOTH skips, separated only by their reason.
# tests/test_hook_gate.py records the sharpest instance in its own docstring -
# six arms skipping to a green exit 0 with the six reasons never printed - and
# ends "Closing that means changing CI, which is outside this file."
#
# .githooks/pre-push was taught this already and passes -rs to both of its
# invocations; tests/test_prepush_skip_reporting.py grades that. ci.yml was
# never taught the same thing. These arms are that guard's twin for CI.
#
# SCOPE, STATED RATHER THAN IMPLIED. These arms read BOTH workflows.
# docs-guards.yml also invokes pytest twice, on a DERIVED list of md-reading
# modules expanded from a shell array (`"${app[@]}"`), and until 2026-09-09
# neither of those invocations carried an `-r` spec. That was a real instance
# of the same blind spot, left open because docs-guards.yml sat outside the
# write-list of the slice that added the ci.yml arms - applicable-and-not-done
# rather than not-applicable. It is closed below, and this paragraph no longer
# describes the tree as it was.
#
# THE TWO FLOORS ARE NOT THE SAME SHAPE, and that is forced rather than
# chosen. ci.yml names its suites literally, so CI_SUITE_TARGETS can be typed
# by hand and compared against what the scan reads. docs-guards.yml cannot be
# graded that way: its guard list is derived at CI time from `git ls-files`
# and reaches pytest as a shell array expansion, so the operand on each
# command line is the literal text `${app[@]}` and no hand-typed path could
# ever match it. The floor there claims only what the mechanism can actually
# claim - exactly two invocations, each targeting the expansion it is meant to
# be - and claims NOTHING about which modules the runner finally collects.
# A path-shaped floor there would not be a stronger guard; it would be a
# permanent red dressed as one.
# ---------------------------------------------------------------------------

# THE PARSER IS SHARED, NOT REIMPLEMENTED, and that is deliberate rather than
# lazy.
#
# tests/test_prepush_skip_reporting.py already carries a token scan hardened
# against the exact trap this arm walks into. Its predecessor keyed on the
# literal string `-rs` and went RED on `-rA`, on `-r s`, on a line continuation
# and on a reordering - four CORRECT invocations. Widening the matcher was the
# wrong response, and it was still wrong the second time. The widened version
# was then measured going GREEN on `-m pytest -r tests`, having read the
# letters of a directory name as an `-r` spec because the word contains an `s`.
# The fix was to stop guessing: an attached spec, or a detached token drawn
# entirely from pytest's own `-r` alphabet, is read; ANYTHING ELSE is reported
# UNPARSEABLE and FAILS.
#
# A private second copy here would be a second chance to reintroduce every one
# of those. .githooks/pre-push states the rule in as many words about its own
# interpreter selector: three private copies of one selector is how a defect
# gets fixed in one place and left live in two.
#
# The cost is a premise shared between two guards, and CLAUDE.md is explicit
# that agreement between two things sharing an input is not evidence. So the
# shared input is TESTED HERE TOO, against ci.yml-shaped text rather than
# hook-shaped text, by the positive control at the bottom of this file.
from tests.test_prepush_skip_reporting import (  # noqa: E402
    PytestInvocation,
    parse_pytest_invocations,
    spec_reports_skips,
)

#: The two targets pytest.ini mandates be invoked SEPARATELY. Typed by hand
#: rather than read out of ci.yml: a census that reads its own answer from the
#: file it audits is not a census.
CI_SUITE_TARGETS = ("tests", "agents/pity_engine")

#: docs-guards.yml's two pytest operands, as the shared token scan reads them.
#: NOT paths, and not a typo - see the scope paragraph above. MEASURED by
#: running `parse_pytest_invocations` over the shipped workflow on 2026-09-09
#: rather than assumed; the scan strips the quotes and keeps the expansion.
DOCS_GUARDS_SUITE_TARGETS = ("${app[@]}", "${engine[@]}")


def _skip_reporting_problems(text: str, source: str) -> list[str]:
    """Every pytest invocation in `text` that will not name its skips.

    Two ways to land on this list, and the second is the important one:

      - the `-r` spec carries none of s, a or A, so pytest prints a bare `s`
        and no reason. `-rfE` is the sting: it HAS an `-r`, so any check that
        merely looks for the flag waves it through.
      - the invocation is UNPARSEABLE. A token scan cannot tell `-r <spec>`
        from `-r` followed by a target, and no regex resolves that, so the
        shared parser refuses to guess and this function refuses to grade a
        subject it cannot read. An unreadable invocation is a FAILURE - never a
        pass, and never a skip.
    """
    problems: list[str] = []
    for inv in parse_pytest_invocations(text):
        if inv.unparseable:
            problems.append(
                f"{source}: the invocation targeting {inv.target!r} carries an `-r` this "
                f"scan cannot read ({inv.unparseable}), so it reports FAILURE rather than a "
                f"green it cannot justify - attach the spec to the flag, as in `-rs`"
            )
            continue
        if not spec_reports_skips(inv.r_spec):
            problems.append(
                f"{source}: the invocation targeting {inv.target!r} has `-r` spec "
                f"{inv.r_spec!r}, none of whose characters lists skips, so its skips reach "
                f"the log as bare `s` characters with no reason - add s, a or A"
            )
    return problems


def test_pytest_ini_does_not_itself_supply_the_skip_reporting_the_workflow_adds():
    """PREMISE, as its own arm, the same shape as the doubled-q premise above.

    The guard below is only meaningful while pytest.ini leaves `-r` unset. If a
    skip-reporting spec were ever added to `addopts`, every invocation in the
    tree would report skips whatever the workflow passed, and this guard would
    silently become a rule about nothing while still looking like protection.
    """
    addopts = [
        ln for ln in PYTEST_INI.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("addopts")
    ]
    assert addopts, "pytest.ini has no addopts line"
    specs = [tok for ln in addopts for tok in ln.split("#")[0].split() if tok.startswith("-r")]
    assert not specs, (
        f"pytest.ini's addopts now carries {specs}. If that spec reports skips, the guard "
        f"below is guarding nothing and should be deleted rather than left looking like "
        f"protection; re-read both files before changing either."
    )


def test_the_shared_parser_reads_the_real_ci_workflow():
    """NON-VACUITY for the import itself, before anything is graded with it.

    The parser is a token scan of shell lines and ci.yml is YAML. If a future
    edit moved these steps into a shape the scan cannot see - a composite
    action, a `uses:`, a matrix - it would find zero invocations and the guard
    below would pass over an empty list forever. That is precisely the vacuous
    pass this module exists to catch elsewhere.
    """
    invocations = parse_pytest_invocations(CI.read_text(encoding="utf-8"))
    assert invocations, (
        f"the shared token scan found no `-m pytest` invocation in {CI.name} at all. Either "
        f"the suites left this workflow, or they are now invoked in a shape a shell token "
        f"scan cannot read; either way the guard below is grading nothing."
    )


def test_every_ci_pytest_invocation_names_its_skips_and_both_suites_are_present():
    """THE GUARD, with its own anti-vacuity floor INSIDE the same assertion.

    A floor kept in a separate arm leaves this one vacuous in the window where
    the floor is red - "every invocation reports skips" is trivially true of
    zero invocations, and of two invocations that are no longer the suites. So
    the census and the judgement are ONE assert: both mandated suite targets
    must be present, AND no invocation anywhere in the workflow may be silent
    or unreadable.

    WHAT THIS CAN CLAIM, narrow on purpose. It claims that each `-m pytest`
    line the scan can see requests a short summary whose spec includes skips.
    It does NOT claim the flag survives to the runner - a variable, an `eval`,
    a composite action or a sourced fragment would all be invisible - it does
    not model YAML, and it does not assert step ORDER, because reordering two
    independent suites is a correct workflow.
    """
    text = CI.read_text(encoding="utf-8")
    invocations = parse_pytest_invocations(text)
    targets = {inv.target for inv in invocations}

    problems: list[str] = []
    missing = [t for t in CI_SUITE_TARGETS if t not in targets]
    if missing:
        problems.append(
            f"{CI.name} no longer invokes {missing} as its own pytest command, so a rule "
            f"about 'every invocation' would be a rule about the wrong set. Found targets: "
            f"{sorted(targets)}"
        )
    suite_invocations = [inv for inv in invocations if inv.target in CI_SUITE_TARGETS]
    if len(suite_invocations) < len(CI_SUITE_TARGETS):
        problems.append(
            f"{CI.name} carries {len(suite_invocations)} suite invocation(s); pytest.ini "
            f"mandates {len(CI_SUITE_TARGETS)}, run SEPARATELY and never merged into one "
            f"root-level collection"
        )
    problems.extend(_skip_reporting_problems(text, CI.name))

    assert not problems, (
        "CI will report a skip COUNT it cannot explain. Measured on run 34343895319: "
        "`1 failed, 1636 passed, 19 skipped in 24.30s` with none of the nineteen named, "
        "against 1 skip for the same tree on Windows. A skip whose reason is absent is "
        "indistinguishable from a test that was never written.\n  - "
        + "\n  - ".join(problems)
    )


def test_the_shared_parser_reads_the_real_docs_guards_workflow():
    """NON-VACUITY for the import against the SECOND subject, not a duplicate.

    The ci.yml arm above proves the scan can see THAT file. It says nothing
    about this one, and this one has the harder shape: two `if` blocks nested
    inside a single `run: |`, each expanding a shell array that an earlier step
    built. If a future edit moved that into a composite action, a matrix, a
    `uses:` or a helper script, the scan would find zero invocations and the
    guard below would pass over an empty list forever - the exact vacuous pass
    this module exists to catch elsewhere.
    """
    invocations = parse_pytest_invocations(DOCS_GUARDS.read_text(encoding="utf-8"))
    assert invocations, (
        f"the shared token scan found no `-m pytest` invocation in {DOCS_GUARDS.name} at "
        f"all. Either the md-reading guards stopped being run, or they are now invoked in "
        f"a shape a shell token scan cannot read; either way the guard below is grading "
        f"nothing."
    )


def test_every_docs_guards_pytest_invocation_names_its_skips():
    """THE GUARD for docs-guards.yml, with its floor INSIDE the same assertion.

    Same reasoning as the ci.yml arm: a floor kept in a separate arm leaves
    this one vacuous in the window where the floor is red, because "every
    invocation reports skips" is trivially true of zero invocations. So the
    census and the judgement are ONE assert.

    THE FLOOR IS DIFFERENT IN KIND, and deliberately weaker than ci.yml's.
    There the targets are literal suite paths. Here they are shell array
    expansions of a list derived at CI time, so the strongest TRUE statement
    available is that the workflow still runs pytest exactly twice and that
    each invocation still targets the expansion it is meant to be - one per
    bucket, never merged. Whether those arrays are non-empty, and what they
    contain, is a runtime property this scan cannot reach; that is graded
    instead by `test_the_suite_split_is_load_bearing_and_not_decoration`, and
    the workflow itself prints a `::notice::` rather than a silent green when
    both come back empty.

    ORDER IS NOT ASSERTED. Running the engine bucket first would be a correct
    workflow, so the comparison is over the multiset.
    """
    text = DOCS_GUARDS.read_text(encoding="utf-8")
    invocations = parse_pytest_invocations(text)
    targets = sorted(inv.target for inv in invocations)

    problems: list[str] = []
    if targets != sorted(DOCS_GUARDS_SUITE_TARGETS):
        problems.append(
            f"{DOCS_GUARDS.name} should invoke pytest exactly "
            f"{len(DOCS_GUARDS_SUITE_TARGETS)} times, once per derived bucket, targeting "
            f"{sorted(DOCS_GUARDS_SUITE_TARGETS)}; the token scan found {targets}. If the "
            f"buckets were renamed, update DOCS_GUARDS_SUITE_TARGETS in the same commit - "
            f"do not delete this floor, or the rule below becomes a rule about zero "
            f"invocations"
        )
    problems.extend(_skip_reporting_problems(text, DOCS_GUARDS.name))

    assert not problems, (
        "the guard step is the ONLY step in the docs-guards job that runs assertions, and "
        "with no `-r` spec its skips reach the log as bare `s` characters - a count with "
        "no reasons, in the one job a docs-only commit triggers at all. "
        "ran-and-found-nothing and not-present-at-all are both skips, separated only by "
        "the text this flag prints.\n  - "
        + "\n  - ".join(problems)
    )


def test_the_skip_detector_flags_shapes_a_narrower_matcher_would_wave_through():
    """POSITIVE CONTROL over hand-typed workflow text, in BOTH directions.

    A control that plants only the case the matcher handles cannot discover
    that the matcher is narrow, so the FLAGGED side varies the shape across the
    ways an invocation can fail to name its skips, and the SURVIVING side
    varies it across the spellings that are CORRECT and were measured false
    reds in the guard this idiom replaces. An accept-only control passes for a
    detector welded to False; a reject-only control passes for one welded to
    True.

    Written as YAML `run:` fragments rather than bare shell lines, because that
    is the shape the real subject has - a parser that only worked on
    hook-style lines would be a shared premise nobody had tested here.
    """
    flagged = {
        "no -r at all - the form ci.yml shipped before this commit": (
            "      - name: Application suite (tests/)\n"
            "        run: python -m pytest tests\n"
        ),
        "an -r that does NOT list skips - defeats any check for the flag alone": (
            "      - name: Engine suite\n"
            "        run: python -m pytest -rfE agents/pity_engine\n"
        ),
        "a detached -r whose next token is a target and not a spec": (
            "      - name: Application suite\n"
            "        run: python -m pytest -r tests\n"
        ),
        "a bare -r at end of line, with the target ahead of it": (
            "      - name: Engine suite\n"
            "        run: python -m pytest agents/pity_engine -r\n"
        ),
        "a skip-reporting spec sitting in a COMMENT while the command has none": (
            "      # the suites pass -rs so the log names every skip\n"
            "        run: python -m pytest tests\n"
        ),
    }
    for shape, snippet in flagged.items():
        found = _skip_reporting_problems(snippet, "control.yml")
        assert found, f"the detector waved through {shape}:\n{snippet}"

    surviving = {
        "-rs attached, the form ci.yml now ships": (
            "        run: python -m pytest -rs tests\n"
        ),
        "-rA, which reports strictly MORE and was a measured false red": (
            "        run: python -m pytest -rA agents/pity_engine\n"
        ),
        "-r s detached but drawn from pytest's own -r alphabet": (
            "        run: python -m pytest -r s tests\n"
        ),
        "a continuation line, which a windowed regex splits in half": (
            "        run: |\n"
            "          python -m pytest -rsx \\\n"
            "            agents/pity_engine\n"
        ),
        "a reordering, with the target ahead of the flag": (
            "        run: python -m pytest tests -ra\n"
        ),
        "an env prefix, as the hook-gate step carries": (
            "        run: RSC_REQUIRE_HOOK_GATE=1 python -m pytest -rs tests/test_hook_gate.py\n"
        ),
    }
    for shape, snippet in surviving.items():
        found = _skip_reporting_problems(snippet, "control.yml")
        assert not found, f"the detector went RED on a CORRECT invocation - {shape}: {found}"


def test_the_control_snippets_are_actually_parsed_and_not_silently_empty():
    """NON-VACUITY FOR THE CONTROL ITSELF, and it is not a formality.

    `_skip_reporting_problems` returns an empty list both for text whose
    invocations are all correct AND for text in which it found no invocation at
    all. The surviving side of the control above cannot tell those apart, so a
    typo that made a snippet unparseable would read there as a pass. This arm
    pins that each surviving snippet yields exactly one invocation, with the
    target and the spec it was written to carry.
    """
    cases = (
        ("        run: python -m pytest -rs tests\n", "tests", "s"),
        ("        run: python -m pytest -rA agents/pity_engine\n", "agents/pity_engine", "A"),
        ("        run: python -m pytest -r s tests\n", "tests", "s"),
        ("        run: python -m pytest tests -ra\n", "tests", "a"),
        (
            "        run: |\n          python -m pytest -rsx \\\n            agents/pity_engine\n",
            "agents/pity_engine",
            "sx",
        ),
    )
    for snippet, target, spec in cases:
        parsed = parse_pytest_invocations(snippet)
        assert parsed == [PytestInvocation(target, spec, "")], (
            f"the control snippet {snippet!r} parsed as {parsed!r}, so its empty problem "
            f"list said nothing at all about skip reporting"
        )
        assert spec_reports_skips(spec), f"{spec!r} must report skips or the case is wrong"
