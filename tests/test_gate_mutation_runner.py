"""The gate mutation runner's machinery, graded against hand-typed sources.

WHY THIS SUITE NEVER RUNS PYTEST AND NEVER TOUCHES THE REAL RESPONDER.

`tools/gate_mutation_runner.py` exists to answer the one question the gate
census cannot: is a tagged gate EXERCISED by anything? It answers it by
disabling a gate and watching whether `python -m pytest tests` goes red. That
is a ~35 minute hand-run campaign that rewrites `tools/moon_sync_responder.py`
in place, so it is emphatically not a pytest gate and this module does not
invoke it as one. What this module grades is the MACHINERY - the tag grammar,
the four mutation shapes, the restore discipline and the classifier - against
synthetic sources typed out by hand.

HAND-TYPED IS THE LOAD-BEARING WORD. This tree's standing lesson is that a
grading arm which consults the same predicate as the thing it grades cannot see
that predicate be wrong: if the expected mutant text were computed by calling
the runner's own generator, the arm would assert only that the generator equals
itself. So every expected mutant below is written out in full, character by
character, and compared as a whole string.

The two arms that DO read the live responder carry their anti-vacuity floor
WELDED INTO THE SAME ASSERTION as the judgement. A floor asserted in a separate
arm leaves the primary arm free to pass on an empty plan - the arm would be
making a statement about nothing while reading as green.
"""

from __future__ import annotations

import ast
import hashlib
import shutil
from collections import Counter
from pathlib import Path

import pytest

from tools import gate_mutation_runner as gmr

REPO_ROOT = Path(__file__).resolve().parents[1]
RESPONDER = REPO_ROOT / "tools" / "moon_sync_responder.py"

# Measured against the live responder on 2026-09-09 at 199aaae: 18 tags,
# 14 If + 1 Try + 1 Assign/IfExp + 2 Assign/BoolOp, 35 mutants. The floors
# below sit UNDER the measurement deliberately - they are a vacuity floor, not
# a restatement of the census, which already pins the exact tag set. A count
# guard that must be edited every time a gate is added earns nothing here.
MIN_LIVE_GATES = 18
MIN_LIVE_MUTANTS = 30


# --------------------------------------------------------------------------
# Synthetic sources. One per mutable shape, plus one unsupported shape.
# --------------------------------------------------------------------------

SYN_IF = (
    "def _run_once(flag):\n"
    "    result = 0\n"
    "    # GATE:alpha-one\n"
    "    if flag:\n"
    "        result = 1\n"
    "    return result\n"
)

SYN_IF_TRUE = (
    "def _run_once(flag):\n"
    "    result = 0\n"
    "    # GATE:alpha-one\n"
    "    if True:\n"
    "        result = 1\n"
    "    return result\n"
)

SYN_IF_FALSE = (
    "def _run_once(flag):\n"
    "    result = 0\n"
    "    # GATE:alpha-one\n"
    "    if False:\n"
    "        result = 1\n"
    "    return result\n"
)

SYN_TRY = (
    "def _run_once(fn):\n"
    "    # GATE:beta\n"
    "    try:\n"
    "        return fn()\n"
    "    except ValueError:\n"
    "        # a comment ahead of the body stays put\n"
    "        note = 'caught'\n"
    "        return note\n"
    "    except OSError:\n"
    "        return 'io'\n"
)

SYN_TRY_MUTANT = (
    "def _run_once(fn):\n"
    "    # GATE:beta\n"
    "    try:\n"
    "        return fn()\n"
    "    except ValueError:\n"
    "        # a comment ahead of the body stays put\n"
    "        raise\n"
    "    except OSError:\n"
    "        raise\n"
)

SYN_IFEXP = (
    "def _run_once(flag):\n"
    "    # GATE:gamma\n"
    "    label = 'yes' if flag else 'no'\n"
    "    return label\n"
)

SYN_IFEXP_TRUE = (
    "def _run_once(flag):\n"
    "    # GATE:gamma\n"
    "    label = 'yes' if True else 'no'\n"
    "    return label\n"
)

SYN_IFEXP_FALSE = (
    "def _run_once(flag):\n"
    "    # GATE:gamma\n"
    "    label = 'yes' if False else 'no'\n"
    "    return label\n"
)

SYN_BOOLOP = (
    "def _run_once(a, b):\n"
    "    # GATE:delta\n"
    "    ok = bool(a) and all(x for x in b)\n"
    "    return ok\n"
)

SYN_BOOLOP_FIRST = (
    "def _run_once(a, b):\n"
    "    # GATE:delta\n"
    "    ok = bool(a)\n"
    "    return ok\n"
)

SYN_BOOLOP_SECOND = (
    "def _run_once(a, b):\n"
    "    # GATE:delta\n"
    "    ok = all(x for x in b)\n"
    "    return ok\n"
)

SYN_WHILE = (
    "def _run_once(n):\n"
    "    # GATE:epsilon\n"
    "    while n > 0:\n"
    "        n -= 1\n"
    "    return n\n"
)


def _sources(mutants: list[gmr.Mutant]) -> list[str]:
    return [m.source for m in mutants]


# --------------------------------------------------------------------------
# Tag grammar.
# --------------------------------------------------------------------------


def test_a_well_formed_tag_is_found() -> None:
    """The happy path, so the near-miss arms below are not vacuously green."""
    tags = gmr.find_gate_tags(SYN_IF)
    assert [(t.name, t.line) for t in tags] == [("alpha-one", 3)]


@pytest.mark.parametrize(
    "bad",
    [
        "    # GATE: spaced\n",
        "    # GATE:Upper\n",
        "    # GATE:under_score\n",
        "    # GATE:\n",
        "    # GATE:name # trailing\n",
    ],
)
def test_a_near_miss_tag_raises_rather_than_reading_as_absent(bad: str) -> None:
    """FAIL LOUD, NEVER FAIL OPEN.

    A single strict regex has already failed open once in this tree: the census
    step found `# GATE: draft-skip` - one space after the colon - invisible to
    it, and a tag that is invisible is indistinguishable from a gate that was
    never tagged. So the detector is permissive and the grammar is strict, and
    the gap between them RAISES.
    """
    source = "def _run_once(flag):\n" + bad + "    if flag:\n        return 1\n    return 0\n"
    with pytest.raises(gmr.GateTagError) as excinfo:
        gmr.find_gate_tags(source)
    message = str(excinfo.value)
    assert "2" in message and bad.strip() in message, message


def test_a_trailing_comment_on_a_code_line_is_not_a_tag() -> None:
    """Only a WHOLE-LINE comment is a tag - and the near-miss must not fire."""
    source = "def _run_once(flag):\n    x = 1  # GATE:name\n    return x\n"
    assert gmr.find_gate_tags(source) == []


# --------------------------------------------------------------------------
# The four shapes. Expected mutant text is typed out, never computed.
# --------------------------------------------------------------------------


def test_an_if_gate_yields_a_true_mutant_and_a_false_mutant() -> None:
    mutants, unmutatable = gmr.plan_mutants(SYN_IF)
    assert unmutatable == []
    assert [m.gate for m in mutants] == ["alpha-one", "alpha-one"]
    assert _sources(mutants) == [SYN_IF_TRUE, SYN_IF_FALSE]


def test_a_try_gate_yields_one_mutant_that_neutralises_every_handler() -> None:
    """One mutant, all handlers. A catch that nothing depends on is the defect."""
    mutants, unmutatable = gmr.plan_mutants(SYN_TRY)
    assert unmutatable == []
    assert [m.gate for m in mutants] == ["beta"]
    assert _sources(mutants) == [SYN_TRY_MUTANT]


def test_an_ifexp_assign_gate_forces_its_test_both_ways() -> None:
    mutants, unmutatable = gmr.plan_mutants(SYN_IFEXP)
    assert unmutatable == []
    assert [m.gate for m in mutants] == ["gamma", "gamma"]
    assert _sources(mutants) == [SYN_IFEXP_TRUE, SYN_IFEXP_FALSE]


def test_a_boolop_assign_gate_yields_one_mutant_per_operand() -> None:
    """Dropping one operand is how a vacuous-`all([])` guard gets caught."""
    mutants, unmutatable = gmr.plan_mutants(SYN_BOOLOP)
    assert unmutatable == []
    assert [m.gate for m in mutants] == ["delta", "delta"]
    assert _sources(mutants) == [SYN_BOOLOP_FIRST, SYN_BOOLOP_SECOND]


def test_an_unsupported_shape_is_reported_not_skipped() -> None:
    """A silently skipped gate reads exactly like a gate with no survivors."""
    mutants, unmutatable = gmr.plan_mutants(SYN_WHILE)
    assert mutants == []
    assert [(u.gate, u.line, u.shape) for u in unmutatable] == [("epsilon", 2, "While")]


def test_the_gate_filter_selects_by_name() -> None:
    source = SYN_IF + "\n\n" + SYN_IFEXP.replace("_run_once", "_other").replace("gamma", "zeta")
    every, _ = gmr.plan_mutants(source)
    only_alpha, _ = gmr.plan_mutants(source, gates=["alpha-one"])
    assert [m.gate for m in every] == ["alpha-one", "alpha-one"]
    assert [m.gate for m in only_alpha] == ["alpha-one", "alpha-one"]
    assert gmr.plan_mutants(source, gates=["nothing-named-this"]) == ([], [])


# --------------------------------------------------------------------------
# Every mutant parses, and edits nothing outside the tagged statement.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "label"),
    [(SYN_IF, "if"), (SYN_TRY, "try"), (SYN_IFEXP, "ifexp"), (SYN_BOOLOP, "boolop")],
)
def test_a_synthetic_mutant_parses_and_is_a_pure_edit_of_its_statement(source: str, label: str) -> None:
    mutants, _ = gmr.plan_mutants(source)
    assert mutants, label
    for mutant in mutants:
        ast.parse(mutant.source)
        _assert_edit_confined(source, mutant)


def test_every_live_mutant_parses_and_is_a_pure_edit_of_its_statement() -> None:
    """Live arm. The floor rides INSIDE the assertion, not beside it."""
    source = RESPONDER.read_text(encoding="ascii")
    mutants, unmutatable = gmr.plan_mutants(source)
    for mutant in mutants:
        ast.parse(mutant.source)
        _assert_edit_confined(source, mutant)
    assert len(mutants) >= MIN_LIVE_MUTANTS and not unmutatable, (
        f"the confinement claim above is only worth the plan it ran over: "
        f"{len(mutants)} mutants (floor {MIN_LIVE_MUTANTS}), unmutatable={unmutatable}"
    )


def _assert_edit_confined(original: str, mutant: gmr.Mutant) -> None:
    """No byte outside the tagged node's line range may move."""
    before = original.split("\n")
    after = mutant.source.split("\n")
    head = mutant.first_line - 1
    tail = len(before) - mutant.last_line
    assert before[:head] == after[:head], f"{mutant.gate}/{mutant.label}: text above the node moved"
    if tail:
        assert before[-tail:] == after[-tail:], f"{mutant.gate}/{mutant.label}: text below the node moved"
    assert mutant.source != original, f"{mutant.gate}/{mutant.label}: mutant is a no-op"


def test_the_live_plan_is_the_measured_shape_census() -> None:
    """Live arm. Floor and judgement in one assertion, again deliberately."""
    source = RESPONDER.read_text(encoding="ascii")
    tags = gmr.find_gate_tags(source)
    mutants, unmutatable = gmr.plan_mutants(source)
    per_gate = Counter(m.gate for m in mutants)
    assert (
        len(tags) >= MIN_LIVE_GATES
        and len(mutants) >= MIN_LIVE_MUTANTS
        and not unmutatable
        and set(per_gate) == {t.name for t in tags}
    ), (
        f"tags={len(tags)} (floor {MIN_LIVE_GATES}) mutants={len(mutants)} "
        f"(floor {MIN_LIVE_MUTANTS}) unmutatable={unmutatable} "
        f"untouched={sorted({t.name for t in tags} - set(per_gate))}"
    )


# --------------------------------------------------------------------------
# Restore discipline. Driven over a temporary copy with an injected runner.
# --------------------------------------------------------------------------


def _synthetic_target(tmp_path: Path) -> Path:
    target = tmp_path / "synthetic_responder.py"
    target.write_bytes(SYN_IF.encode("ascii"))
    return target


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_a_campaign_restores_the_target_byte_for_byte(tmp_path: Path) -> None:
    target = _synthetic_target(tmp_path)
    before = target.read_bytes()
    seen: list[str] = []

    def stub(mutant: gmr.Mutant) -> int:
        seen.append(target.read_text(encoding="ascii"))
        return 1

    mutants, _ = gmr.plan_mutants(SYN_IF)
    results = gmr.run_campaign(target, mutants, stub, repo_root=tmp_path)

    assert seen == [SYN_IF_TRUE, SYN_IF_FALSE], "the stub did not observe the mutated file on disk"
    assert target.read_bytes() == before
    assert [r.killed for r in results] == [True, True]


def test_a_campaign_restores_the_target_even_when_the_suite_runner_raises(tmp_path: Path) -> None:
    """try/finally, not best effort. An abandoned mutant is a poisoned tree."""
    target = _synthetic_target(tmp_path)
    before = target.read_bytes()

    def exploding(mutant: gmr.Mutant) -> int:
        raise KeyboardInterrupt

    mutants, _ = gmr.plan_mutants(SYN_IF)
    with pytest.raises(KeyboardInterrupt):
        gmr.run_campaign(target, mutants, exploding, repo_root=tmp_path)

    assert target.read_bytes() == before


def test_the_campaign_purges_bytecode_on_both_sides_of_every_mutation(tmp_path: Path) -> None:
    """The net-zero-size restore that ran the MUTANT'S bytecode is why.

    Windows filesystem mtime granularity is coarse enough that a mutate and a
    restore inside the same second leave a `__pycache__` entry that still looks
    current, so the interpreter serves the mutant's compiled bytes against
    restored source. Measured in this tree: a red suite against hashes matching
    HEAD.
    """
    target = _synthetic_target(tmp_path)
    nested = tmp_path / "pkg" / "__pycache__"
    nested.mkdir(parents=True)
    (nested / "stale.pyc").write_bytes(b"stale")
    survivors: list[bool] = []

    def stub(mutant: gmr.Mutant) -> int:
        survivors.append(nested.exists())
        (nested / "stale.pyc").parent.mkdir(parents=True, exist_ok=True)
        (nested / "stale.pyc").write_bytes(b"stale again")
        return 1

    mutants, _ = gmr.plan_mutants(SYN_IF)
    gmr.run_campaign(target, mutants, stub, repo_root=tmp_path)

    assert survivors == [False, False], "bytecode survived into a mutated run"
    assert not nested.exists(), "bytecode survived the restore"


# --------------------------------------------------------------------------
# The classifier and the exit code.
# --------------------------------------------------------------------------


def test_a_nonzero_suite_exit_kills_and_a_zero_exit_survives(tmp_path: Path) -> None:
    target = _synthetic_target(tmp_path)
    codes = iter([0, 3])

    def stub(mutant: gmr.Mutant) -> int:
        return next(codes)

    mutants, _ = gmr.plan_mutants(SYN_IF)
    results = gmr.run_campaign(target, mutants, stub, repo_root=tmp_path)
    assert [(r.exit_code, r.killed) for r in results] == [(0, False), (3, True)]


def test_main_exits_one_when_a_mutant_survives(tmp_path: Path) -> None:
    target = _synthetic_target(tmp_path)
    report = tmp_path / "report.txt"
    code = gmr.main(
        ["--target", str(target), "--report", str(report), "--repo-root", str(tmp_path)],
        suite_runner=lambda mutant: 0,
    )
    body = report.read_text(encoding="ascii")
    assert code == 1
    assert "SURVIVED" in body and "alpha-one" in body


def test_main_exits_zero_when_every_mutant_is_killed(tmp_path: Path) -> None:
    target = _synthetic_target(tmp_path)
    report = tmp_path / "report.txt"
    code = gmr.main(
        ["--target", str(target), "--report", str(report), "--repo-root", str(tmp_path)],
        suite_runner=lambda mutant: 1,
    )
    body = report.read_text(encoding="ascii")
    assert code == 0
    assert "SURVIVED" not in body and body.count("KILLED") >= 2


def test_the_report_is_written_with_lf_endings(tmp_path: Path) -> None:
    """`write_text` translates LF to CRLF on Windows and `eol=lf` hides it."""
    target = _synthetic_target(tmp_path)
    report = tmp_path / "report.txt"
    gmr.main(
        ["--target", str(target), "--report", str(report), "--repo-root", str(tmp_path)],
        suite_runner=lambda mutant: 1,
    )
    assert b"\r\n" not in report.read_bytes()


# --------------------------------------------------------------------------
# --dry-run and --list touch nothing.
# --------------------------------------------------------------------------


def test_dry_run_over_the_live_responder_writes_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    """Live arm. The floor is welded to the untouched-bytes claim."""
    before = _digest(RESPONDER)
    code = gmr.main(["--dry-run"])
    printed = capsys.readouterr().out
    after = _digest(RESPONDER)
    assert (
        code == 0
        and after == before
        and printed.count("\n") >= MIN_LIVE_MUTANTS
    ), f"digest {before} -> {after}, {printed.count(chr(10))} lines printed"


def test_dry_run_never_calls_the_suite_runner(tmp_path: Path) -> None:
    target = _synthetic_target(tmp_path)
    before = target.read_bytes()

    def forbidden(mutant: gmr.Mutant) -> int:
        raise AssertionError("--dry-run ran the suite")

    assert gmr.main(["--target", str(target), "--dry-run"], suite_runner=forbidden) == 0
    assert target.read_bytes() == before


def test_list_prints_the_live_tags_and_touches_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    """Live arm, floor welded in: --list must name at least the measured gates."""
    before = _digest(RESPONDER)
    code = gmr.main(["--list"])
    printed = capsys.readouterr().out
    named = [line for line in printed.split("\n") if line.strip()]
    assert (
        code == 0
        and _digest(RESPONDER) == before
        and len(named) >= MIN_LIVE_GATES
        and "counterparty-agreement" in printed
    ), f"{len(named)} lines printed"


# --------------------------------------------------------------------------
# Shape of the tool itself.
# --------------------------------------------------------------------------


def test_the_default_report_path_is_gitignored() -> None:
    """A report under a tracked path would be a merge conflict every campaign."""
    relative = gmr.DEFAULT_REPORT.relative_to(REPO_ROOT).as_posix()
    assert relative.startswith("ops/runtime/")
    ignore = (REPO_ROOT / ".gitignore").read_text(encoding="ascii")
    assert "ops/runtime/*" in ignore


def test_the_campaign_suite_excludes_this_module_and_the_path_it_names_exists() -> None:
    """THIS MODULE MAY NOT GRADE THE CAMPAIGN, and the ignore must be real.

    Measured 2026-09-09. The live arms above read the responder and assert the
    SHAPE of the plan derived from it. The four operand mutants of
    `bounce-write-all` and `delivery-write-all` rewrite a boolean operation into
    a plain call, so this module went red on 2 arms for each of them - and being
    alphabetically ahead of the responder's own modules, under `-x` it aborted
    the run before they were reached. The campaign would have recorded KILLED
    while learning nothing about whether any test drives that gate.

    The second half of the assertion is the non-vacuity control. An `--ignore`
    of a path that does not exist is a silent no-op that reads exactly like a
    working exclusion, so this arm would go on passing after a rename while the
    confound quietly came back.
    """
    argv = gmr.suite_argv("tests")
    assert (
        f"--ignore={gmr.SELF_TEST_MODULE}" in argv
        and (REPO_ROOT / gmr.SELF_TEST_MODULE).resolve() == Path(__file__).resolve()
        and "-x" in argv
        and "-q" not in argv
    ), argv


def test_the_census_is_excluded_as_a_shape_grader_and_the_path_is_the_file_it_means() -> None:
    """The census grades the TARGET FILE'S SHAPE, so it cannot grade a campaign.

    RE-MEASURED IN THIS TREE at e87e26c on 2026-09-09, full runs, no `-x`,
    caches purged on both sides, this module ignored throughout so that only the
    census varied. Each of `bounce-write-all/operand-1`, `.../operand-2`,
    `delivery-write-all/operand-1` and `.../operand-2` gave, with the census
    included, 32 failed 1755 passed 1 skipped exit 1 - all 32 failing nodes in
    `tests/test_responder_gate_census.py` and none anywhere else - and, with the
    census ignored, 1716 passed 1 skipped exit 0. They SURVIVE. The campaign had
    reported all four as KILLED.

    The path check is the non-vacuity half: pytest ignores an unknown `--ignore`
    silently, so a rename would leave this arm green and the confound live. It
    is not enough that some file is there, so the arm also confirms the module
    is the one that reads the responder.
    """
    census = "tests/test_responder_gate_census.py"
    argv = gmr.suite_argv("tests")
    path = REPO_ROOT / census
    assert census in gmr.SHAPE_GRADER_MODULES, gmr.SHAPE_GRADER_MODULES
    assert f"--ignore={census}" in argv, argv
    assert path.is_file(), path
    assert "moon_sync_responder" in path.read_text(encoding="ascii")


def test_the_name_bindings_module_is_excluded_and_is_the_file_it_means() -> None:
    """A WIDER shape grader than the census, and the census's confinement fails.

    `tests/test_gate_name_bindings.py` binds each of the 18 `# GATE:` tags to
    the line immediately below it by STRING EQUALITY against a hand-typed
    anchor. The census grades an AST, so it can only false-kill a mutant that
    changes AST shape - 4 of 35. An equality on a line's literal bytes has no
    such ceiling: `if not usable:` becoming `if True:` leaves the AST the census
    grades intact and destroys the equality this module grades.

    MEASURED IN THIS TREE at f571234 on 2026-09-09 without running pytest, by
    planning the live mutants and asking this module's own `_violations`
    instrument about each mutant source: 35 mutants planned, 0 unmutatable, 0
    anchor violations on the CLEAN responder, and 34 of the 35 mutant sources
    producing at least one anchor violation. The sole exception is
    `spawn-failure/except-reraise`, whose anchor is the bare line `try:` while
    the mutation rewrites the handler body underneath it.

    Undeclared, that module would let a campaign print 34 syntax reddenings as
    KILLED and exit 0.

    The path half is the non-vacuity control, as in the census arm above: an
    `--ignore` of a path pytest cannot find is a silent no-op, so this arm would
    stay green through a rename while the confound came back. Confirming the
    file also READS the responder is what makes it the module this exclusion
    means rather than merely some file at that path.
    """
    bindings = "tests/test_gate_name_bindings.py"
    argv = gmr.suite_argv("tests")
    path = REPO_ROOT / bindings
    assert bindings in gmr.SHAPE_GRADER_MODULES, gmr.SHAPE_GRADER_MODULES
    assert f"--ignore={bindings}" in argv, argv
    assert path.is_file(), path
    source = path.read_text(encoding="ascii")
    assert "moon_sync_responder" in source
    assert "read_text" in source


def test_the_two_exclusion_reasons_are_named_apart_not_merged() -> None:
    """One list, two arguments, and a reader must be able to tell them apart.

    "This module decides its own verdict" and "this module grades the target
    file's shape" are different claims with different consequences, so they live
    in different constants. Merging them would leave the next person to add an
    exclusion with no way to say which argument they are invoking.

    STRENGTHENED, NOT WEAKENED, when `SHAPE_GRADER_MODULES` grew to 2. The four
    assertions this arm carried were all arity-agnostic - `EXCLUDED_MODULES ==
    (SELF_TEST_MODULE, *SHAPE_GRADER_MODULES)` holds for a list of any length -
    so all four went on passing unchanged through the second entry landing, and
    the arm said nothing whatever about it. That is the failure this file's own
    header calls a grading arm that cannot see the thing it grades be wrong.

    So the arity is now PINNED, and the claim that carries the actual weight is
    added: each shape grader must have its OWN reason in prose, in the comment
    block between the two constants. One list with two entries and one shared
    paragraph is the merged state this arm exists to forbid, and it is reachable
    without touching either constant's name.
    """
    assert gmr.SELF_TEST_MODULE not in gmr.SHAPE_GRADER_MODULES
    assert gmr.EXCLUDED_MODULES == (gmr.SELF_TEST_MODULE, *gmr.SHAPE_GRADER_MODULES)
    assert len(set(gmr.EXCLUDED_MODULES)) == len(gmr.EXCLUDED_MODULES)
    assert [name for name in gmr.EXCLUDED_MODULES if f"--ignore={name}" in gmr.suite_argv("tests")] == list(
        gmr.EXCLUDED_MODULES
    )

    assert len(gmr.SHAPE_GRADER_MODULES) == 2, gmr.SHAPE_GRADER_MODULES
    assert len(gmr.EXCLUDED_MODULES) == 3, gmr.EXCLUDED_MODULES

    runner = (REPO_ROOT / "tools" / "gate_mutation_runner.py").read_text(encoding="ascii")
    self_at = runner.index("\nSELF_TEST_MODULE = ")
    shape_at = runner.index("\nSHAPE_GRADER_MODULES: ")
    assert self_at < shape_at, (self_at, shape_at)
    shape_prose = runner[self_at:shape_at]
    for name in gmr.SHAPE_GRADER_MODULES:
        assert name in shape_prose, name
    assert "SECOND ENTRY" in shape_prose, "the second grader has no reason of its own"


def test_every_declared_exclusion_exists_and_the_detector_fires_on_one_that_does_not() -> None:
    """The guard, and the arm proving the guard is not a decoration.

    MEASURED 2026-09-09: `--ignore=tests/does_not_exist_xyz.py` collected 107
    tests and reported no error at all. A missing exclusion is therefore
    indistinguishable from a working one from the outside, which is precisely
    the failure this detector exists to convert into a crash.
    """
    assert gmr.missing_exclusions(REPO_ROOT) == []
    gmr.verify_exclusions(REPO_ROOT)

    bogus = ("tests/does_not_exist_xyz.py", gmr.SELF_TEST_MODULE)
    assert gmr.missing_exclusions(REPO_ROOT, bogus) == ["tests/does_not_exist_xyz.py"]
    with pytest.raises(gmr.ExclusionError) as caught:
        gmr.verify_exclusions(REPO_ROOT, bogus)
    assert "does_not_exist_xyz" in str(caught.value)


# --------------------------------------------------------------------------
# The opposite question. `missing_exclusions` walks the DECLARED sequence and
# asks of each declared path whether it is real, so the only thing it can ever
# find is a STALE declaration. Nothing enumerated the corpus, so a module that
# grades the target's shape and sits in NOBODY'S list was never looked at.
#
# Every fixture below is HAND-TYPED, for the reason the kill-site section
# states: a grading arm that derives its corpus the same way the detector does
# cannot see that derivation be wrong.
# --------------------------------------------------------------------------

#: BINDS the responder at module level and LATER READS it. A candidate.
FAKE_READER = (
    "from pathlib import Path\n"
    "\n"
    'TARGET = Path(__file__).parent / "tools" / "moon_sync_responder.py"\n'
    'LIVE = TARGET.read_text(encoding="ascii")\n'
    "\n"
    "\n"
    "def test_the_shape_is_what_it_was():\n"
    '    assert "def _run_once" in LIVE\n'
)

#: MENTIONS the responder and never opens it. The control for question two -
#: naming is not reading, and most modules in this tree that mention the
#: responder only ever mention it.
FAKE_MENTIONER = (
    'NOTE = "tools/moon_sync_responder.py is only named here, never opened"\n'
    "\n"
    "\n"
    "def test_the_note_says_so():\n"
    '    assert "moon_sync_responder" in NOTE\n'
)

#: READS a file and never binds the responder. The control for question one -
#: a detector keyed on `.read_text` alone would flag half the tree.
FAKE_OTHER_READER = (
    "from pathlib import Path\n"
    "\n"
    'OTHER = Path(__file__).parent / "tools" / "some_other_module.py"\n'
    'BODY = OTHER.read_text(encoding="ascii")\n'
    "\n"
    "\n"
    "def test_the_other_body_is_there():\n"
    "    assert BODY\n"
)


def _plant(root: Path, name: str, source: str) -> str:
    """Write one hand-typed corpus member as LF ASCII and return its relpath.

    `write_bytes`, never `write_text`. `Path.write_text` translates LF to CRLF
    on Windows and `.gitattributes eol=lf` hides it from every diff, so a
    fixture written the convenient way is a fixture whose bytes are not the
    bytes that were typed.
    """
    data = source.encode("ascii")
    assert b"\r\n" not in data, name
    (root / name).write_bytes(data)
    return name


def test_the_sweep_finds_every_responder_reader_and_every_one_is_declared() -> None:
    """ONE WELDED ASSERTION: a floor, the three known readers, and the subset.

    The three claims are welded because separating them makes the load-bearing
    one vacuous. "Every reader found is declared" is trivially true of an empty
    result, and an empty result is exactly what a broken corpus derivation or a
    silently over-narrowed detector produces. A floor sitting in an arm of its
    own does not protect this arm, because the two can pass in different runs.

    MEASURED IN THIS TREE at f571234 on 2026-09-09: 129 tracked `.py` files, 13
    of them mentioning `moon_sync_responder` anywhere, and exactly 3 candidates
    with no false positives - the two shape graders and this module, which is a
    genuine responder reader excluded under the OTHER reason. That is why
    `undeclared_shape_graders` subtracts all of `EXCLUDED_MODULES` and not just
    `SHAPE_GRADER_MODULES`.
    """
    known = {
        "tests/test_gate_mutation_runner.py",
        "tests/test_gate_name_bindings.py",
        "tests/test_responder_gate_census.py",
    }
    found = gmr.responder_reading_modules(REPO_ROOT)
    assert (
        found
        and known <= set(found)
        and set(found) <= set(gmr.EXCLUDED_MODULES)
        and gmr.undeclared_shape_graders(REPO_ROOT) == []
    ), (found, gmr.EXCLUDED_MODULES)


def test_the_undeclared_detector_fires_on_a_planted_reader_and_not_on_a_declared_one(
    tmp_path: Path,
) -> None:
    """The detector FIRES, plus the CONTROL that it does not fire on everything.

    Without the control arm this proves nothing: a detector that returns its
    whole input would pass the firing half and be useless. So the SAME corpus
    is swept twice, and the only thing that changes between the two sweeps is
    whether the planted reader is declared.

    The two non-candidates are in the corpus for both sweeps. They are what
    makes the first result a discrimination rather than a count.
    """
    corpus = [
        _plant(tmp_path, "fake_reader.py", FAKE_READER),
        _plant(tmp_path, "fake_mentioner.py", FAKE_MENTIONER),
        _plant(tmp_path, "fake_other_reader.py", FAKE_OTHER_READER),
    ]
    assert len(corpus) == 3, corpus

    assert gmr.responder_reading_modules(tmp_path, corpus) == ["fake_reader.py"]

    fires = gmr.undeclared_shape_graders(tmp_path, corpus, excluded=())
    control = gmr.undeclared_shape_graders(tmp_path, corpus, excluded=("fake_reader.py",))
    assert fires == ["fake_reader.py"] and control == [], (fires, control)


def test_verify_exclusions_raises_a_distinct_type_per_check(tmp_path: Path) -> None:
    """TWO CHECKS, TWO TYPES, and an arm that can tell which one fired.

    A single shared exception type makes the two indistinguishable, and an arm
    pinning a type both raise proves nothing about which check ran. Both stay
    under `ExclusionError` so a caller that only cares that the campaign refused
    still catches both - hence the sibling-negative assertion on each, which is
    the half that would go vacuous if the subclasses were ever collapsed.
    """
    corpus = [
        _plant(tmp_path, "fake_reader.py", FAKE_READER),
        _plant(tmp_path, "fake_mentioner.py", FAKE_MENTIONER),
    ]

    with pytest.raises(gmr.UndeclaredShapeGraderError) as undeclared:
        gmr.verify_exclusions(tmp_path, ("fake_mentioner.py",), corpus)
    assert isinstance(undeclared.value, gmr.ExclusionError)
    assert not isinstance(undeclared.value, gmr.MissingExclusionError)
    assert "fake_reader.py" in str(undeclared.value)

    with pytest.raises(gmr.MissingExclusionError) as missing:
        gmr.verify_exclusions(tmp_path, ("nope_not_here.py",), corpus)
    assert isinstance(missing.value, gmr.ExclusionError)
    assert not isinstance(missing.value, gmr.UndeclaredShapeGraderError)
    assert "nope_not_here.py" in str(missing.value)

    assert gmr.MissingExclusionError is not gmr.UndeclaredShapeGraderError


# --------------------------------------------------------------------------
# Which test killed a mutant. Every sample below is HAND-TYPED.
#
# A grading arm that consults the same parser as the thing it grades cannot see
# that parser be wrong, so none of these fixtures is produced by running pytest
# or by calling the runner. They are transcribed by hand from observed output.
# --------------------------------------------------------------------------

PYTEST_X_FAILURE = (
    "=================================== FAILURES ===================================\n"
    "_______________________ test_an_armed_run_marks_the_hop ________________________\n"
    "\n"
    "    def test_an_armed_run_marks_the_hop():\n"
    ">       assert marked == 1\n"
    "E       assert 0 == 1\n"
    "\n"
    "tests\\test_moon_sync_responder.py:412: AssertionError\n"
    "=========================== short test summary info ============================\n"
    "FAILED tests/test_moon_sync_responder.py::test_an_armed_run_marks_the_hop - assert 0 == 1\n"
    "!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!\n"
    "1 failed, 214 passed in 8.11s\n"
)

PYTEST_X_CENSUS_FAILURE = (
    "=========================== short test summary info ============================\n"
    "FAILED tests/test_responder_gate_census.py::test_every_tag_sits_above_a_branch - AssertionError: "
    "GATE:bounce-write-all is not immediately above an If, a Try, or an assignment\n"
    "1 failed, 31 passed in 2.04s\n"
)

PYTEST_COLLECTION_ERROR = (
    "==================================== ERRORS ====================================\n"
    "________________ ERROR collecting tests/test_moon_sync_responder.py ____________\n"
    "E   ImportError: cannot import name '_run_once'\n"
    "=========================== short test summary info ============================\n"
    "ERROR tests/test_moon_sync_responder.py\n"
    "!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!!\n"
)

PYTEST_QQ_NO_SUMMARY = "1 failed, 1716 passed, 1 skipped in 39.07s\n"

NOT_A_NODE_ID = (
    "FAILED to reach the responder on port 8790 - connection refused\n"
    "ERROR while writing the inbox receipt\n"
    "1 failed in 0.90s\n"
)

TWO_FAILURES = (
    "=========================== short test summary info ============================\n"
    "FAILED tests/test_alpha.py::test_first - assert 1 == 2\n"
    "FAILED tests/test_beta.py::test_second - assert 3 == 4\n"
    "2 failed in 1.10s\n"
)


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (PYTEST_X_FAILURE, "tests/test_moon_sync_responder.py::test_an_armed_run_marks_the_hop"),
        (
            PYTEST_X_CENSUS_FAILURE,
            "tests/test_responder_gate_census.py::test_every_tag_sits_above_a_branch",
        ),
        (PYTEST_COLLECTION_ERROR, "tests/test_moon_sync_responder.py"),
        (TWO_FAILURES, "tests/test_alpha.py::test_first"),
    ],
)
def test_the_kill_site_parser_reads_the_first_failing_node(output: str, expected: str) -> None:
    """A kill has to name its killer, and it comes out of output already held."""
    assert gmr.parse_first_failure(output) == expected


@pytest.mark.parametrize("output", [PYTEST_QQ_NO_SUMMARY, NOT_A_NODE_ID, "", "collected 1819 items\n"])
def test_an_unreadable_output_degrades_to_unknown_and_never_to_a_wrong_name(output: str) -> None:
    """Honest None, not a guess.

    `-qq` suppresses the short summary; a line beginning FAILED may be prose
    rather than a node id. The whole point of the field is to expose a kill that
    came from the wrong module, so a confident wrong name is worse than nothing.
    """
    assert gmr.parse_first_failure(output) is None


def test_a_result_with_no_node_id_reports_unknown_rather_than_a_module() -> None:
    mutant = gmr.Mutant(gate="alpha-one", label="if-true", source=SYN_IF_TRUE, first_line=4, last_line=5)
    result = gmr.MutantResult(mutant=mutant, exit_code=1, killed=True)
    assert result.kill_site == "unknown"
    assert result.kill_module is None
    assert result.false_kill is False
    assert result.verdict == "KILLED"


def test_a_kill_by_a_shape_grader_is_a_false_kill_and_a_kill_by_anything_else_is_not() -> None:
    """The census reddening over an AST is not evidence that a gate is driven."""
    mutant = gmr.Mutant(gate="alpha-one", label="if-true", source=SYN_IF_TRUE, first_line=4, last_line=5)
    census = gmr.MutantResult(
        mutant=mutant,
        exit_code=1,
        killed=True,
        node_id="tests/test_responder_gate_census.py::test_every_tag_sits_above_a_branch",
    )
    behavioural = gmr.MutantResult(
        mutant=mutant,
        exit_code=1,
        killed=True,
        node_id="tests/test_moon_sync_responder.py::test_an_armed_run_marks_the_hop",
    )
    assert census.false_kill is True and census.verdict == "FALSE-KILL"
    assert behavioural.false_kill is False and behavioural.verdict == "KILLED"


def test_the_report_names_the_killing_test_and_shouts_about_a_false_kill(tmp_path: Path) -> None:
    """A report that says only KILLED could not have shown this defect.

    It did not: the four false kills were found by a refuter running the suite
    by hand. The loud arm below is paired with the quiet one so that a change
    which shouts about every kill fails too.
    """
    target = _synthetic_target(tmp_path)
    report = tmp_path / "report.txt"
    outcomes = iter(
        [
            gmr.SuiteOutcome(1, "tests/test_responder_gate_census.py::test_every_tag_sits_above_a_branch"),
            gmr.SuiteOutcome(1, "tests/test_moon_sync_responder.py::test_an_armed_run_marks_the_hop"),
        ]
    )
    code = gmr.main(
        ["--target", str(target), "--report", str(report), "--repo-root", str(tmp_path)],
        suite_runner=lambda mutant: next(outcomes),
    )
    body = report.read_text(encoding="ascii")

    assert code == 1, "a false kill is not a clean campaign"
    assert "FALSE KILLS - THESE ARE NOT KILLS" in body
    assert "killed-by=tests/test_responder_gate_census.py::test_every_tag_sits_above_a_branch" in body
    assert "killed-by=tests/test_moon_sync_responder.py::test_an_armed_run_marks_the_hop" in body
    assert "2 mutants, 1 killed, 0 survived, 1 false kills" in body, body


def test_a_clean_campaign_says_nothing_about_false_kills(tmp_path: Path) -> None:
    """The non-vacuity partner: the shout must be conditional, not unconditional."""
    target = _synthetic_target(tmp_path)
    report = tmp_path / "report.txt"
    code = gmr.main(
        ["--target", str(target), "--report", str(report), "--repo-root", str(tmp_path)],
        suite_runner=lambda mutant: gmr.SuiteOutcome(
            1, "tests/test_moon_sync_responder.py::test_an_armed_run_marks_the_hop"
        ),
    )
    body = report.read_text(encoding="ascii")
    assert code == 0
    assert "FALSE KILL" not in body
    assert "2 mutants, 2 killed, 0 survived, 0 false kills" in body


def test_importing_the_runner_touches_no_file(tmp_path: Path) -> None:
    """It must be importable without side effects - a pytest run imports it."""
    copied = tmp_path / "copy.py"
    shutil.copyfile(gmr.__file__, copied)
    before = _digest(RESPONDER)
    source = copied.read_text(encoding="ascii")
    module = ast.parse(source)
    toplevel_calls = [
        node
        for node in module.body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    ]
    assert toplevel_calls == []
    assert _digest(RESPONDER) == before


#: The four modules that bind the responder at module level to a plain `Name`
#: and then read it through `importlib.util.spec_from_file_location`. They pass
#: criterion 1 of `_binds_and_reads_responder` and fail criterion 2, so the
#: detector misses all four - and they are NOT declared, deliberately, because
#: they import the responder to exercise its BEHAVIOUR rather than to grade its
#: shape. Hand-typed, in sorted order, and NOT derived by re-running the
#: detector: a list computed from the predicate under grading can only ever
#: agree with itself.
IMPORTLIB_READERS = (
    "tests/test_moon_sync_responder.py",
    "tests/test_responder_broadcast_refusal.py",
    "tests/test_responder_delivery_gates.py",
    "tests/test_responder_refusal_gates.py",
)


def _module_level_responder_names(source: str) -> set[str]:
    """Plain `Name` targets of a module-level assignment mentioning the responder.

    This is criterion 1 of `_binds_and_reads_responder`, RE-TYPED rather than
    imported, so that the arm below is a statement about the shape of those four
    modules and not a statement about the detector agreeing with itself.
    """
    names: set[str] = set()
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign) or node.value is None:
            continue
        if "moon_sync_responder" not in ast.unparse(node.value):
            continue
        names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    return names


def test_the_detector_states_the_importlib_route_it_cannot_see() -> None:
    """ONE WELDED ASSERTION: the written ceiling, and the four real modules under it.

    A written limit with no instrument watching it is the prose-decay class this
    tree keeps recording, so the ceiling sentence is pinned. Pinning prose alone
    would be the OTHER failure, though - a docstring can describe a blind spot
    that does not exist - so the same arm re-derives the blind spot from the four
    modules themselves: each really does bind the responder at module level to a
    plain `Name`, really does read it through
    `importlib.util.spec_from_file_location`, and really is missed.

    THE CONTROL IS WELDED IN TOO. `responder_reading_modules` must still name
    the three declared readers on the live corpus, otherwise a detector that had
    silently stopped finding ANYTHING would satisfy every clause above by
    returning False for the whole tree.
    """
    doc = gmr._binds_and_reads_responder.__doc__ or ""
    for phrase in ("importlib", "spec_from_file_location", "15 IS A LOWER BOUND", "15 DISTINCT REPO FILES"):
        assert phrase in doc, phrase
    for name in IMPORTLIB_READERS:
        assert name in doc, name

    for name in IMPORTLIB_READERS:
        path = REPO_ROOT / name
        source = path.read_text(encoding="utf-8")
        assert _module_level_responder_names(source), name
        assert "spec_from_file_location" in source, name
        assert gmr._binds_and_reads_responder(source) is False, name
        assert name not in gmr.EXCLUDED_MODULES, name

    assert set(gmr.responder_reading_modules(REPO_ROOT)) == {
        "tests/test_gate_mutation_runner.py",
        "tests/test_gate_name_bindings.py",
        "tests/test_responder_gate_census.py",
    }


def test_the_false_kill_property_cannot_fire_under_the_campaign_argv() -> None:
    """`false_kill` is a DIAGNOSTIC, and the unreachability is derived here, not asserted.

    Derived: every name in `SHAPE_GRADER_MODULES` is `--ignore`d by
    `suite_argv`, so a real campaign never collects one, so no node id it parses
    can name one, so the property is structurally False for every mutant of a
    real campaign.

    THE NON-VACUITY PARTNER IS IN THE SAME ARM. The property must still return
    True for a hand-built result naming a shape grader - that is the bypassed
    path it exists to serve - and False for one naming a behavioural module.
    Without that pair this arm would pass equally well against a property that
    was hard-wired to False, which is the thing it is trying to distinguish
    itself from.

    The ceiling sentence is pinned with it, including the pointer to
    `undeclared_shape_graders` as the only LIVE protection, because that pointer
    is the part a reader needs and the part prose decay would take first.
    """
    argv = gmr.suite_argv("tests")
    assert [name for name in gmr.SHAPE_GRADER_MODULES if f"--ignore={name}" in argv] == list(
        gmr.SHAPE_GRADER_MODULES
    ), argv
    assert set(gmr.SHAPE_GRADER_MODULES) <= set(gmr.EXCLUDED_MODULES)
    assert gmr.SHAPE_GRADER_MODULES, gmr.SHAPE_GRADER_MODULES

    mutant = gmr.Mutant(gate="alpha-one", label="if-true", source=SYN_IF_TRUE, first_line=4, last_line=5)
    bypassed = gmr.MutantResult(
        mutant=mutant,
        exit_code=1,
        killed=True,
        node_id=f"{gmr.SHAPE_GRADER_MODULES[0]}::test_anything",
    )
    behavioural = gmr.MutantResult(
        mutant=mutant,
        exit_code=1,
        killed=True,
        node_id="tests/test_moon_sync_responder.py::test_an_armed_run_marks_the_hop",
    )
    assert bypassed.false_kill is True and behavioural.false_kill is False

    doc = gmr.MutantResult.false_kill.__doc__ or ""
    for phrase in (
        "DIAGNOSTIC AND NOT A LIVE PROTECTION",
        "BYPASSED",
        "undeclared_shape_graders",
        "spec_from_file_location",
    ):
        assert phrase in doc, phrase
