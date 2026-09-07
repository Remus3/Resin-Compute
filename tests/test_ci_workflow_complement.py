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
someone who already opened the right file. Riot Commander enforces this
mechanically in CI (its "docs-guard complement is wired" step); this tree had
the comment and no enforcement until now.

Parsed with a line scanner rather than a YAML library because this repository is
stdlib-only at runtime and PyYAML is not a dependency. The scan is deliberately
narrow - it reads the two `on:` trigger blocks and nothing else.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

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
    """
    out = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        timeout=120,
    )
    assert out.returncode == 0, f"git {' '.join(args)} failed: {out.stderr!r}"
    return [p for p in out.stdout.decode("utf-8", "surrogateescape").split("\0") if p]


def _listed(mode: str) -> set[str]:
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
    """
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
    """NON-VACUITY for the arm above: the probe must reject a committable path."""
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
