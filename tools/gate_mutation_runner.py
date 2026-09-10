"""Mutation-test the tagged gates in the responder's cycle. HAND-RUN, not a gate.

WHAT THIS ANSWERS THAT THE CENSUS CANNOT.

`tests/test_responder_gate_census.py` guards that every branch in the
responder's cycle carries a tag and that the tags are well named. Its own stated
ceiling is that it says nothing about whether a gate is EXERCISED: nothing there
drives a gate, and nothing there asks whether disabling one turns a suite red.

That distinction is not theoretical here. Measured before this tool existed:
three mutants disabled a gate inside `_run_once` and the application suite
stayed GREEN, because every arm tested the gate's PREDICATE as a pure function
and nothing tested that the cycle consults it. A predicate can be right, tested,
and ignored.

So this tool reads the tags, generates one mutant per way of neutralising the
tagged statement, writes each over the responder in turn, runs the application
suite, and reports which mutants SURVIVED. A survivor names a gate that no test
in the campaign suite depends on - the campaign suite being the application
suite minus `EXCLUDED_MODULES`, which is a narrower and more honest claim than
"no test depends on it".

USAGE

    python -m tools.gate_mutation_runner --list
    python -m tools.gate_mutation_runner --dry-run
    python -m tools.gate_mutation_runner --gate bounce-mark
    python -m tools.gate_mutation_runner

Exit code is 1 if any mutant SURVIVED or if any kill was a FALSE KILL, 0 only if
every mutant was killed by a test that grades behaviour. Gates whose tagged
statement has no supported shape are reported as unmutatable in the report
header - they are NOT silently skipped, because a skipped gate reads exactly
like a gate with no survivors.

WHAT A KILL MEANS, AND HOW A KILL CAN BE FALSE.

A non-zero exit says the suite went red. It does not say WHY. If the module that
went red grades the TARGET FILE'S SHAPE rather than the responder's behaviour,
the redness is about syntax and the mutant is not killed at all - it is
unmeasured. That is not hypothetical: the first campaign this tool ran reported
31 killed and 4 survived, and four of those kills were the census reddening over
an AST it no longer recognised. The corrected score is 27 killed and 8 survived,
and the eighth survivor is a real vacuous guard nothing tests. See
`SHAPE_GRADER_MODULES` for the measurement.

Two things follow, and both are in this file. Shape-grading modules are excluded
from the campaign suite by name, and every excluded name is checked to EXIST
because an `--ignore` of a missing path is a silent no-op. And every kill now
records WHICH TEST killed it, parsed out of the pytest output already captured,
so a kill from the wrong kind of module is visible in the report instead of
being something a later reader has to re-derive by hand.

WHY IT IS NOT A PYTEST GATE. A full campaign is 35 mutants against a suite whose
clean run is roughly a minute, so a green campaign costs well over half an hour.
That belongs in a hand-run tool and a recorded report, not in a suite anyone is
expected to run before a commit. `tests/test_gate_mutation_runner.py` grades
this module's machinery against synthetic sources and never invokes pytest.

THE FOUR TRAPS THIS FILE IS SHAPED AROUND, all measured in this tree.

1. A mutate-and-restore inside the same second runs the MUTANT'S BYTECODE
   against restored source. Windows filesystem mtime granularity is coarser
   than the edit, so a `__pycache__` entry that is stale still looks current.
   Hence `purge_caches` after every write AND after the restore, over the whole
   repo tree rather than beside the file.
2. Restore comes from bytes held in memory and is verified by SHA256. Never
   `git checkout --`: that restores what HEAD says, not what was there, and a
   tool that silently reverts an uncommitted edit is worse than a crash.
3. Textual substitution is done on AST spans, not on `str.replace`. A
   `replace` of `if not usable:` would hit every identical line in the file.
4. `Path.write_text` translates LF to CRLF on Windows and `.gitattributes
   eol=lf` hides it from every diff, so every write here is `write_bytes`.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The file whose tags this tool consumes.
RESPONDER = REPO_ROOT / "tools" / "moon_sync_responder.py"

#: The function whose branches carry the tags.
FUNCTION = "_run_once"

#: Under `ops/runtime/`, which `.gitignore` excludes as `ops/runtime/*`. A
#: report on a tracked path would be a merge conflict every campaign.
DEFAULT_REPORT = REPO_ROOT / "ops" / "runtime" / "gate_mutation_report.txt"

#: PERMISSIVE detector. Anything that a reader would call a gate tag.
#:
#: The census step measured why this is not one regex: a strict pattern alone
#: FAILED OPEN on `# GATE: draft-skip` - one space after the colon - and an
#: invisible tag is indistinguishable from an untagged gate. The gap between
#: the two patterns below raises rather than shrugging.
#:
#: It anchors the `#` to the start of the line, so a trailing comment on a code
#: line is not a tag and is not a near-miss either.
_PERMISSIVE = re.compile(r"^[ \t]*#.*\bgate\b[ \t]*:", re.IGNORECASE)

#: STRICT grammar: a whole-line comment reading exactly hash, space, GATE,
#: colon, name - uppercase GATE, no space after the colon, nothing after the
#: name, name in lowercase-hyphen form.
_STRICT = re.compile(r"^[ \t]*# GATE:([a-z0-9]+(?:-[a-z0-9]+)*)$")

#: EXCLUSION ONE - A MODULE THAT DECIDES ITS OWN VERDICT.
#:
#: This tool's OWN test module. MEASURED 2026-09-09, and it is a real confound
#: rather than tidiness. That module reads the live responder and asserts the
#: shape of the plan derived from it, so a mutant that changes a statement's
#: SHAPE makes it go red - the four operand mutants of `bounce-write-all` and
#: `delivery-write-all` rewrite a boolean operation into a plain call, and the
#: module failed 2 arms on each. Under `-x` it also collects before the
#: responder's own modules, so it would abort the run first and the campaign
#: would record KILLED while learning nothing about whether any test drives that
#: gate. A grader that consults the file under mutation is not a grader.
#:
#: THE SENTENCE THAT USED TO STAND HERE WAS TRUE AND ITS CONCLUSION WAS FALSE.
#: It read: "with this module ignored, all four still die on the rest of the
#: suite, so the verdict did not depend on the confound." They did still die -
#: on `tests/test_responder_gate_census.py`, which is the same class of confound
#: one module over, and the verdict depended on it entirely. What the exclusion
#: below fixes, and what `KILL_SITE_HELP` exists to make visible, is exactly
#: that: a claim of independence had to be MEASURED per module, and it was not.
SELF_TEST_MODULE = "tests/test_gate_mutation_runner.py"

#: EXCLUSION TWO - A MODULE THAT GRADES THE TARGET FILE'S SHAPE.
#:
#: A DIFFERENT REASON, kept in a DIFFERENT CONSTANT on purpose. Exclusion one is
#: "this module decides its own verdict". This one is "this module answers a
#: question about SYNTAX while the campaign is asking a question about
#: BEHAVIOUR". Collapsing the two into one list would leave a later reader
#: unable to tell which argument applies to which path, and the arguments have
#: different consequences: exclusion one would be wrong to apply to a module the
#: tool does not ship, and exclusion two is a template for every future module
#: that reads `tools/moon_sync_responder.py` and asserts things about its AST.
#:
#: `tests/test_responder_gate_census.py` reads the responder AT IMPORT - see its
#: module-level `_LIVE_SOURCE = RESPONDER.read_text(...)` - and grades the
#: resulting AST. A mutant that removes a `BoolOp` operand from a tagged
#: statement changes that AST, so the census reddens over syntax and not over
#: any responder behaviour being exercised. Its failure text is pure shape:
#: "GATE:bounce-write-all is not immediately above an If, a Try, or an
#: assignment writing a chosen value into a subscript". Under `-x` that is
#: indistinguishable from a real kill, and for four mutants it WAS mistaken for
#: one - the campaign reported 31 killed and 4 survived where the truth is 27
#: and 8.
#:
#: RE-MEASURED IN THIS TREE at e87e26c on 2026-09-09, full runs, no `-x`, caches
#: purged on both sides of every mutation, `tests/test_gate_mutation_runner.py`
#: ignored throughout so only the census varies:
#:
#:   bounce-write-all/operand-1    census included: 32 failed, 1755 passed,
#:                                 1 skipped, exit 1, 32 of 32 failing nodes in
#:                                 the census and none anywhere else.
#:                                 census ignored:  1716 passed, 1 skipped,
#:                                 exit 0. It SURVIVES.
#:   bounce-write-all/operand-2    same both ways.
#:   delivery-write-all/operand-1  same both ways.
#:   delivery-write-all/operand-2  same both ways.
#:
#: CONFINEMENT, also measured: `if True`, `if False` and the `except`-reraise
#: mutants PRESERVE the AST shape the census grades, so the census cannot false-
#: kill them, and both IfExp mutants are genuine behavioural kills in
#: `tests/test_moon_sync_responder.py`. The defect was confined to the 2 BoolOp
#: gates and their 4 mutants.
#:
#: `delivery-write-all/operand-1` is why this matters rather than being
#: bookkeeping. It drops the `bool(written)` term that the responder's own
#: comment calls THE GUARD, not decoration - the term that stops `all([])`
#: reporting a delivery to zero destinations as delivered. Nothing in the suite
#: tests it, and the old report hid that behind a KILLED.
#:
#: SECOND ENTRY - `tests/test_gate_name_bindings.py`, WITH ITS OWN REASON,
#: WHICH IS NOT THE CENSUS'S AND IS STRICTLY WIDER.
#:
#: The census grades the AST of the tagged statement, so its false kills are
#: CONFINED to the mutants that change AST shape - the 2 BoolOp gates and their
#: 4 mutants, as the confinement paragraph above records, with `if True`,
#: `if False` and the `except`-reraise families provably immune. That
#: confinement argument does NOT carry over, and assuming it would is the trap
#: this paragraph exists to close.
#:
#: The bindings module reads the responder AT IMPORT - `_LIVE_SOURCE =
#: RESPONDER.read_text(...)` at `tests/test_gate_name_bindings.py:79` - and
#: binds each of the 18 `# GATE:<name>` tags to the line IMMEDIATELY BELOW the
#: tag by STRING EQUALITY against a hand-typed anchor in its `_ANCHORS` table.
#: An equality on a line's literal bytes is the WIDEST available shape
#: assertion. Every mutation this tool performs rewrites the text of the tagged
#: statement, so a mutant reddens that module whenever its first rewritten line
#: is an anchored line - whether or not the AST shape survives. `if not usable:`
#: becoming `if True:` preserves the AST the census grades and destroys the
#: equality the bindings module grades.
#:
#: MEASURED IN THIS TREE at f571234 on 2026-09-09, WITHOUT running pytest: the
#: live plan is 35 mutants and 0 unmutatable; the clean responder has 0 anchor
#: violations; and 34 of the 35 mutant sources produce at least one anchor
#: violation. The single exception is `spawn-failure/except-reraise`, whose
#: anchor is the bare line `try:` - the mutation rewrites the handler body
#: below it and leaves the anchored line untouched.
#:
#: 34 of 35 is why this is declared BEFORE its first campaign rather than after
#: a report has been believed. An undeclared module reddening 34 of 35 mutants
#: would let a campaign print 34 syntax reddenings as KILLED and exit 0 - the
#: exact defect the false-kill work exists to prevent, restored at a larger
#: scale than the one it was built to catch, and this time with almost nothing
#: left over to notice it by.
#:
#: This is the case exclusion two was written as a TEMPLATE for; see the
#: sentence above calling it "a template for every future module that reads
#: `tools/moon_sync_responder.py` and asserts things about its AST". The
#: template being correctly applied once is not evidence it will be applied
#: again, which is why `undeclared_shape_graders` below stops the campaign
#: depending on anyone remembering to.
SHAPE_GRADER_MODULES: tuple[str, ...] = (
    "tests/test_responder_gate_census.py",
    "tests/test_gate_name_bindings.py",
)

#: Every path handed to pytest as `--ignore` for a campaign run, in a fixed
#: order so the report's suite line is stable. The two reasons above are the
#: only reasons a module may appear here.
EXCLUDED_MODULES: tuple[str, ...] = (SELF_TEST_MODULE, *SHAPE_GRADER_MODULES)

#: Directories whose contents are compiled or cached artefacts of source.
_CACHE_DIRS = frozenset({"__pycache__", ".pytest_cache"})

#: Never walked. `.git` is large and holds nothing importable.
_WALK_SKIP = frozenset({".git", ".venv", "venv", "node_modules", ".mypy_cache", ".ruff_cache"})


#: Printed beside a kill site the parser could not read. Never a guess.
KILL_SITE_HELP = "unknown"


class GateTagError(ValueError):
    """A line the permissive detector found and the strict grammar rejected."""


class ExclusionError(RuntimeError):
    """Something is wrong with the campaign's exclusion set.

    KEPT AS THE BASE so that a caller which only cares that the campaign
    refused still catches both failures. The two subclasses below exist because
    a caller that catches only this cannot say WHICH check fired, and the two
    checks are opposite questions - see each subclass.
    """


class MissingExclusionError(ExclusionError):
    """A DECLARED path is not a file, so its `--ignore` would be a no-op.

    The declared-side failure. `missing_exclusions` is its detector.
    """


class UndeclaredShapeGraderError(ExclusionError):
    """A REAL module reads the responder and is in NOBODY'S exclusion list.

    The corpus-side failure, and the opposite question from the one above.
    `undeclared_shape_graders` is its detector.
    """


class RestoreError(RuntimeError):
    """The target's bytes after the campaign did not match its bytes before."""


@dataclass(frozen=True)
class GateTag:
    """One well-formed tag: its name and the 1-based line the comment sits on."""

    name: str
    line: int


@dataclass(frozen=True)
class Mutant:
    """One neutralised gate, as a complete source text.

    `first_line` and `last_line` bound the TAGGED STATEMENT, 1-based inclusive.
    Every line outside that range is byte-identical to the original, which is
    what makes a survivor attributable to this gate and not to collateral.
    """

    gate: str
    label: str
    source: str
    first_line: int
    last_line: int

    @property
    def ident(self) -> str:
        return f"{self.gate}/{self.label}"


@dataclass(frozen=True)
class Unmutatable:
    """A tagged statement this tool has no mutation for. Reported, never dropped."""

    gate: str
    line: int
    shape: str


@dataclass(frozen=True)
class SuiteOutcome:
    """One suite run against one mutant: the exit code and where it first died.

    `node_id` is the pytest node id of the FIRST failure, or None when the
    output could not be read. None is a real answer and is reported as
    `killed-by=unknown`; it is never filled in by inference.
    """

    exit_code: int
    node_id: str | None = None


@dataclass(frozen=True)
class MutantResult:
    """A mutant, the suite's exit code, and the verdict that follows from it.

    `node_id` is appended LAST with a default so that every existing positional
    construction, in this tree and in its arms, still builds.
    """

    mutant: Mutant
    exit_code: int
    killed: bool
    node_id: str | None = None

    @property
    def kill_module(self) -> str | None:
        """The module half of `node_id`, in posix form, or None if unread."""
        return failing_module(self.node_id)

    @property
    def kill_site(self) -> str:
        """Where the kill came from, or `unknown`. Never a guess."""
        return self.node_id if self.node_id is not None else KILL_SITE_HELP

    @property
    def false_kill(self) -> bool:
        """A red suite whose first failure was a module that grades SHAPE.

        Such a mutant is NOT killed - it is unmeasured, and the campaign says so
        rather than counting it. The exclusions above are meant to make this
        impossible; this property is what makes a hole in them visible instead
        of silent.

        IT IS A DIAGNOSTIC AND NOT A LIVE PROTECTION, and stating that is the
        whole point of this paragraph. `suite_argv` emits `--ignore` for EVERY
        name in `EXCLUDED_MODULES`, and `SHAPE_GRADER_MODULES` is a subset of
        `EXCLUDED_MODULES` by construction, so under the campaign's own argv
        pytest never COLLECTS a shape grader, `parse_first_failure` can never
        return a node id naming one, and this property is structurally False
        for every mutant of a real campaign. It can be True only where the
        ignore list is BYPASSED: a `suite_runner` that builds its own argv, or
        a caller constructing a `MutantResult` directly, which is exactly what
        this tool's own arms do.

        MAKING IT REACHABLE BY WEAKENING THE EXCLUSIONS WAS CONSIDERED AND
        REJECTED. Dropping the shape graders out of `--ignore` would restore
        the confound the exclusions exist to remove, at the scale measured
        under `SHAPE_GRADER_MODULES` - 34 of the 35 live mutants redden the
        bindings module over syntax alone. A reachable diagnostic bought at
        that price is not protection, it is the defect wearing the detector's
        clothes.

        SO `undeclared_shape_graders` IS THE ONLY LIVE PROTECTION AGAINST A
        HOLE IN THE EXCLUSION LIST, and it is the one with a stated blind spot.
        `_binds_and_reads_responder` cannot see a module that reads the
        responder through `importlib.util.spec_from_file_location`; that limit,
        the four modules it lets through, and the measured population it was
        derived from are written down in that function's docstring. An
        unreachable property that LOOKS like protection is worse than none,
        which is why the reachability is stated here rather than left to be
        inferred by a reader who happens to open `suite_argv`.
        """
        module = self.kill_module
        return self.killed and module is not None and module in SHAPE_GRADER_MODULES

    @property
    def verdict(self) -> str:
        if self.false_kill:
            return "FALSE-KILL"
        return "KILLED" if self.killed else "SURVIVED"


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


def find_gate_tags(source: str) -> list[GateTag]:
    """Every well-formed tag in `source`, in file order.

    Raises `GateTagError` on a near miss - a line that reads as a tag to a human
    and to the permissive detector but fails the strict grammar. Returning it as
    absent is the failure mode this tool cannot afford.
    """
    tags: list[GateTag] = []
    for number, line in enumerate(source.split("\n"), start=1):
        if not _PERMISSIVE.match(line):
            continue
        match = _STRICT.match(line)
        if match is None:
            raise GateTagError(
                f"line {number}: {line.strip()!r} reads as a gate tag but does not match "
                f"the grammar. A tag is a whole-line comment reading exactly "
                f"hash space GATE colon name, with the name in lowercase-hyphen form."
            )
        tags.append(GateTag(name=match.group(1), line=number))
    return tags


# ---------------------------------------------------------------------------
# Source spans. Character offsets, derived from the AST's byte columns.
# ---------------------------------------------------------------------------

_Span = tuple[int, int, int, int]


def _line_starts(source: str) -> list[int]:
    starts = [0]
    for line in source.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _offset(source: str, starts: list[int], lineno: int, col: int) -> int:
    """Absolute character offset of a (1-based line, AST column) pair.

    `col_offset` on an AST node is a UTF-8 BYTE offset into the line, not a
    character offset. This tree is 7-bit ASCII by rule so the two coincide
    today, but converting properly costs one encode and removes the assumption.
    """
    line_start = starts[lineno - 1]
    line = source[line_start : starts[lineno]]
    return line_start + len(line.encode("utf-8")[:col].decode("utf-8", "ignore"))


def _span(node: ast.AST) -> _Span:
    lineno = getattr(node, "lineno", None)
    end_lineno = getattr(node, "end_lineno", None)
    col = getattr(node, "col_offset", None)
    end_col = getattr(node, "end_col_offset", None)
    if lineno is None or end_lineno is None or col is None or end_col is None:
        raise ValueError(f"node {type(node).__name__} carries no source span")
    return (lineno, col, end_lineno, end_col)


def _segment(source: str, starts: list[int], node: ast.AST) -> str:
    lineno, col, end_lineno, end_col = _span(node)
    return source[_offset(source, starts, lineno, col) : _offset(source, starts, end_lineno, end_col)]


def _apply(source: str, starts: list[int], edits: Sequence[tuple[_Span, str]]) -> str:
    """Splice `edits` into `source`. Applied back to front so offsets hold."""
    ordered = sorted(edits, key=lambda edit: _offset(source, starts, edit[0][0], edit[0][1]), reverse=True)
    out = source
    for (lineno, col, end_lineno, end_col), text in ordered:
        start = _offset(source, starts, lineno, col)
        stop = _offset(source, starts, end_lineno, end_col)
        out = out[:start] + text + out[stop:]
    return out


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


def _statements_by_line(function: ast.FunctionDef) -> dict[int, ast.stmt]:
    found: dict[int, ast.stmt] = {}
    for node in ast.walk(function):
        if isinstance(node, ast.stmt):
            found.setdefault(node.lineno, node)
    return found


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _edits_for(source: str, starts: list[int], node: ast.stmt) -> list[tuple[str, list[tuple[_Span, str]]]]:
    """The (label, edits) pairs that neutralise `node`, or [] if the shape is unknown.

    Four shapes, all of which occur live in the responder's cycle:

    - `if` - the test forced True and forced False. Both directions, because a
      gate that only ever falls one way in the suite is half-tested.
    - `try` - every `except` handler body replaced by a bare `raise`, which
      neutralises the catch without removing the handler. One mutant covers all
      handlers: a catch that nothing depends on is the defect, per handler is
      noise.
    - an assignment of a conditional expression - the condition forced both ways.
    - an assignment of a boolean operation - one mutant per operand, each
      dropping the rest. This is the shape that catches a vacuous guard: with
      `all(...) and bool(written)`, dropping `bool(written)` leaves `all([])`
      True for an empty delivery.
    """
    if isinstance(node, ast.If):
        return [
            ("if-true", [(_span(node.test), "True")]),
            ("if-false", [(_span(node.test), "False")]),
        ]

    if isinstance(node, ast.Try):
        if not node.handlers:
            return []
        edits: list[tuple[_Span, str]] = []
        for handler in node.handlers:
            first, last = handler.body[0], handler.body[-1]
            begin = _span(first)
            end = _span(last)
            edits.append(((begin[0], begin[1], end[2], end[3]), "raise"))
        return [("except-reraise", edits)]

    if isinstance(node, ast.Assign) and isinstance(node.value, ast.IfExp):
        test = node.value.test
        return [
            ("ifexp-true", [(_span(test), "True")]),
            ("ifexp-false", [(_span(test), "False")]),
        ]

    if isinstance(node, ast.Assign) and isinstance(node.value, ast.BoolOp):
        whole = _span(node.value)
        return [
            (f"operand-{index}", [(whole, _segment(source, starts, operand))])
            for index, operand in enumerate(node.value.values, start=1)
        ]

    return []


def plan_mutants(
    source: str,
    function_name: str = FUNCTION,
    gates: Iterable[str] | None = None,
) -> tuple[list[Mutant], list[Unmutatable]]:
    """Every mutant the tags in `source` imply, plus the tags with no mutation.

    Derives nothing from the census module's predicates: the tags are read here,
    from the file's own bytes.
    """
    wanted = None if gates is None else set(gates)
    tags = [tag for tag in find_gate_tags(source) if wanted is None or tag.name in wanted]
    if not tags:
        return [], []

    tree = ast.parse(source)
    function = _find_function(tree, function_name)
    if function is None:
        raise ValueError(f"no function named {function_name!r} in the source")
    statements = _statements_by_line(function)
    starts = _line_starts(source)

    mutants: list[Mutant] = []
    unmutatable: list[Unmutatable] = []
    for tag in tags:
        node = statements.get(tag.line + 1)
        if node is None:
            unmutatable.append(Unmutatable(tag.name, tag.line, f"no-statement-in-{function_name}"))
            continue
        plans = _edits_for(source, starts, node)
        if not plans:
            unmutatable.append(Unmutatable(tag.name, tag.line, type(node).__name__))
            continue
        for label, edits in plans:
            mutated = _apply(source, starts, edits)
            mutants.append(
                Mutant(
                    gate=tag.name,
                    label=label,
                    source=mutated,
                    first_line=node.lineno,
                    last_line=node.end_lineno or node.lineno,
                )
            )
    return mutants, unmutatable


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


def purge_caches(root: Path) -> int:
    """Remove every bytecode and pytest cache directory under `root`.

    NOT optional and NOT cosmetic. A mutate-and-restore inside one filesystem
    mtime tick leaves a `__pycache__` entry the interpreter still trusts, and
    the suite then runs the MUTANT'S compiled bytes against restored source.
    That failure was measured here as a red suite whose file hashes all matched
    HEAD, which is unfalsifiable from the diff.
    """
    doomed: list[Path] = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _WALK_SKIP]
        for name in list(dirnames):
            if name in _CACHE_DIRS:
                doomed.append(Path(dirpath) / name)
                dirnames.remove(name)
    removed = 0
    for path in doomed:
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            removed += 1
    return removed


def missing_exclusions(repo_root: Path, excluded: Sequence[str] = EXCLUDED_MODULES) -> list[str]:
    """Every excluded path that is not a file under `repo_root`, in order.

    AN `--ignore` OF A PATH PYTEST CANNOT FIND IS A SILENT NO-OP. Measured
    2026-09-09 in this tree: `--ignore=tests/does_not_exist_xyz.py` collected
    107 tests and said nothing at all. So a rename of an excluded module puts
    the confound straight back while every line of the report still reads the
    same, and the campaign's score quietly stops meaning what it says.

    This is the detector. `verify_exclusions` is the caller that refuses to run
    a campaign when it fires.
    """
    return [name for name in excluded if not (repo_root / name).is_file()]


#: The token a candidate module must bind. The responder's module name rather
#: than its path, so that `REPO_ROOT / "tools" / "moon_sync_responder.py"` and
#: `from tools import moon_sync_responder` both mention it.
_RESPONDER_NEEDLE = "moon_sync_responder"

#: Attribute names that READ a path's bytes. A module that binds the responder
#: and never calls one of these is not reading it.
_READ_ATTRS = frozenset({"read_text", "read_bytes", "open"})


def _binds_and_reads_responder(source: str) -> bool:
    """True when `source` binds the responder at module level and then reads it.

    THE SHAPE OF THIS DETECTOR IS THE SHAPE OF ITS FINDING, so it is written
    narrowly and its cost is stated rather than hidden. It asks two questions
    and takes the conjunction:

    1. Is there a MODULE-LEVEL assignment whose value mentions the responder,
       bound to a plain `Name`? Module level because a grader that reads the
       responder inside one function is a grader for one arm, whereas the
       confound this campaign cares about is a module whose whole verdict is
       derived from the file under mutation.
    2. Is that same name LATER the receiver of `.read_text`, `.read_bytes` or
       `.open`? Naming the responder is not reading it - eight modules in this
       tree mention it in a docstring, an expected-output fixture or an assert
       and never open it.

    WHAT IT CANNOT SEE, stated so a later reader does not mistake a clean sweep
    for a proof. A module that reads the responder through a local variable, a
    fixture, a helper or an import of another module's constant is invisible to
    it - `tools/gate_mutation_runner.py` itself is exactly that case and is
    correctly NOT a candidate, since it reads through the local `path`. So a
    clean result means "no module of this shape is undeclared", never "no
    confound exists". A syntactically broken file is not a candidate either;
    pytest would fail to collect it long before a campaign could be misread.

    THE IMPORTLIB ROUTE IS THE BLIND SPOT INSIDE THE DECLARED SHAPE, and it is
    named here because the list above did not name it and a reader would have
    taken that list for the whole of the cost. FOUR modules -
    `tests/test_moon_sync_responder.py`,
    `tests/test_responder_broadcast_refusal.py`,
    `tests/test_responder_delivery_gates.py` and
    `tests/test_responder_refusal_gates.py` - each bind
    `MODULE = ROOT / "tools" / "moon_sync_responder.py"` AT MODULE LEVEL to a
    plain `Name`, so criterion 1 passes on all four, and then read that name
    through `importlib.util.spec_from_file_location`, where the bound name is
    an ARGUMENT and never the receiver of an attribute access. Criterion 2
    therefore fails and all four are missed.

    `_READ_ATTRS` IS DELIBERATELY NOT WIDENED TO COVER THEM. Those four IMPORT
    the responder to exercise its BEHAVIOUR. They are the tests a campaign
    exists to consult, not graders of the target's shape, so a detector that
    reported them would be wrong on every run and would train a reader to
    ignore it - the same argument already recorded for why
    `undeclared_shape_graders` subtracts all of `EXCLUDED_MODULES` and not just
    `SHAPE_GRADER_MODULES`. Widening a matcher is additionally the repair this
    tree has been defeated by three times, and the standing lesson is that
    after the second defeat you ask what claim the mechanism CAN support rather
    than stretching the match. The honest repair for a detector whose shape is
    its finding is to state the scope.

    THE MEASURED POPULATION, so that "narrow" is a number rather than an
    adjective. Measured in this tree at `6be6961` on 2026-09-09 by a
    `sitecustomize.py` patching `io.open` and `builtins.open` across ONE full
    `python -m pytest tests` run - 1880 passed, 1 skipped: 197 open events on
    `tools/moon_sync_responder.py`, of which 195 attribute to a repo file and 2
    attribute to a frozen pseudo-file frame that is no repo file at all. Those
    195 come from 15 DISTINCT REPO FILES - 14 under `tests/` plus
    `tools/gate_mutation_runner.py`. That population is EVERY FILE THAT OPENS
    THE RESPONDER DURING ONE APPLICATION-SUITE RUN.
    `responder_reading_modules` names 3 of them, and the gap of 12 is not a
    defect: this detector's question is "is a module of THIS SHAPE undeclared",
    and it is never "does anything else read this file".

    15 IS A LOWER BOUND ON THAT POPULATION AND NOT A TOTAL. `importlib` binds
    `io.open_code` inside `_bootstrap_external` before any such patch can land,
    so the import-time reads the four modules above perform are NOT among the
    195 - which is why not one of those four appears in the 15 even though each
    provably reads the file. Reads from subprocesses, and every read performed
    by the `agents/pity_engine` suite, were outside the sample as well. A
    sampled negative is a statement about the sample, so the sampling rule is
    reported beside the number rather than left for a reader to assume away.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    bound: set[str] = set()
    for node in tree.body:
        targets: list[ast.expr]
        value: ast.expr | None
        if isinstance(node, ast.Assign):
            targets, value = list(node.targets), node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if _RESPONDER_NEEDLE not in ast.unparse(value):
            continue
        bound.update(t.id for t in targets if isinstance(t, ast.Name))

    if not bound:
        return False
    return any(
        isinstance(node, ast.Attribute)
        and node.attr in _READ_ATTRS
        and isinstance(node.value, ast.Name)
        and node.value.id in bound
        for node in ast.walk(tree)
    )


def tracked_python_files(repo_root: Path) -> list[str]:
    """Every tracked `.py` path under `repo_root`, posix form, git's order.

    THE CORPUS IS DERIVED FROM `git ls-files`, which is the same command
    `tools/precommit_gate.py`, `tests/test_no_sibling_names.py` and
    `tests/test_docs_consistency.py` build their corpora from. Deriving it the
    same way means an untracked scratch file cannot fail a campaign and a
    tracked module cannot hide from one.
    """
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "ls-files", "--", "*.py"],  # noqa: S607 - git is on PATH by policy
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]


def responder_reading_modules(repo_root: Path, relpaths: Sequence[str] | None = None) -> list[str]:
    """Every module in the corpus that binds the responder and reads it.

    THIS IS THE FUNCTION THAT ENUMERATES THE CORPUS, and its absence was the
    hole. `missing_exclusions` walks the DECLARED sequence and asks of each
    declared path whether it is real; nothing asked the opposite question, so a
    module that grades the target's shape and appears in NOBODY'S list was
    never looked at by anything. A detector that only validates declarations
    can only ever find a stale declaration - never a missing one.

    `relpaths` IS INJECTABLE so an arm can drive a hand-typed corpus. Without
    it every arm would need a git repository in a temp directory, and a
    detector whose arms can only run against the live tree is a detector whose
    firing has never been observed. Passing an explicit sequence skips
    `git ls-files` entirely; passing None derives the corpus from it.

    Paths that do not exist or cannot be decoded are SKIPPED rather than raised
    on: this function answers "which real modules read the responder", and a
    path the caller invented is the other detector's business.
    """
    corpus = tracked_python_files(repo_root) if relpaths is None else [str(p) for p in relpaths]
    found: list[str] = []
    for rel in corpus:
        path = repo_root / rel
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _binds_and_reads_responder(source):
            found.append(rel.replace("\\", "/"))
    return found


def undeclared_shape_graders(
    repo_root: Path,
    relpaths: Sequence[str] | None = None,
    excluded: Sequence[str] = EXCLUDED_MODULES,
) -> list[str]:
    """Responder-reading modules that no exclusion list names, in corpus order.

    SUBTRACTS ALL OF `EXCLUDED_MODULES`, not just `SHAPE_GRADER_MODULES`.
    `tests/test_gate_mutation_runner.py` is a genuine responder-reading module
    and is already excluded under the OTHER reason, so subtracting only the
    shape-grader list would report this tool's own test module as undeclared
    forever and train a reader to ignore the finding.

    Non-empty means a campaign is about to run with a module that can redden
    over syntax while the report calls it a kill.
    """
    declared = {name.replace("\\", "/") for name in excluded}
    return [rel for rel in responder_reading_modules(repo_root, relpaths) if rel not in declared]


def verify_exclusions(
    repo_root: Path,
    excluded: Sequence[str] = EXCLUDED_MODULES,
    relpaths: Sequence[str] | None = None,
) -> None:
    """Refuse a campaign whose exclusion set is wrong in EITHER direction.

    Two checks, TWO DISTINCT EXCEPTION TYPES, both under `ExclusionError`. A
    single shared type would make the two indistinguishable, and an arm pinning
    a type both raise proves nothing about which check ran.

    `MissingExclusionError` - a declared path is not real. `--ignore` of an
    unknown path is a silent no-op.

    `UndeclaredShapeGraderError` - a real shape grader is declared nowhere.
    THIS HARD-FAILS RATHER THAN WARNING, on the same argument that already
    makes the missing-path check raise: a campaign is a half-hour run whose
    output is a file, and a warning inside a report nobody re-reads is exactly
    the failure mode the false-kill work exists to prevent. Refusing to start
    costs one line of typing; a believed report costs the whole campaign.

    `relpaths` is appended LAST with a default so every existing positional
    call still builds.
    """
    missing = missing_exclusions(repo_root, excluded)
    if missing:
        raise MissingExclusionError(
            "these campaign exclusions name paths that do not exist under "
            f"{repo_root}: {', '.join(missing)}. pytest ignores an unknown "
            "--ignore silently, so the campaign would have run with the "
            "confound those paths were named to remove."
        )

    undeclared = undeclared_shape_graders(repo_root, relpaths, excluded)
    if undeclared:
        raise UndeclaredShapeGraderError(
            "these modules under "
            f"{repo_root} read {RESPONDER.name} and are named in no exclusion "
            f"list: {', '.join(undeclared)}. A module that grades the target "
            "file's SHAPE reddens over syntax, and under -x the campaign would "
            "record KILLED while learning nothing about whether any test drives "
            "the gate. Add each to SHAPE_GRADER_MODULES with its OWN measured "
            "reason, or to SELF_TEST_MODULE if it decides this tool's verdict."
        )


def suite_argv(suite: str = "tests") -> list[str]:
    """The pytest argv a campaign runs per mutant.

    `-x` and no `-q`. `-x` makes a kill cheap - a clean full run is around a
    minute, a kill returns in seconds. `-q` is already in `pytest.ini`'s
    `addopts`, and passing it again makes it `-qq`, which suppresses both the
    count line and the short test summary the report parses.

    The `--ignore` flags are load-bearing, not hygiene, and they are there for
    two different reasons - see `SELF_TEST_MODULE` and `SHAPE_GRADER_MODULES`.
    """
    argv = [sys.executable, "-m", "pytest", suite, "-x"]
    argv.extend(f"--ignore={name}" for name in EXCLUDED_MODULES)
    return argv


#: A short-test-summary failure line. The node must LOOK like a node id - a
#: `.py` path, optionally with `::` parts - so that prose after the word FAILED
#: is not read as a test name.
_FAILURE_LINE = re.compile(r"^(?:FAILED|ERROR)[ \t]+(?P<node>[^\s:]\S*\.py(?:::\S+)?)(?:[ \t]|$)")


def parse_first_failure(output: str) -> str | None:
    """The node id of the FIRST failure pytest reported, or None if unreadable.

    Under `-x` pytest stops at the first failure and names it in the short test
    summary as `FAILED <path>::<test> - <reason>`; a failure during collection
    appears as `ERROR <path>`. Both are already in the output the campaign
    captures, so this parses rather than re-running.

    ANYTHING ELSE RETURNS None. A different pytest version, a `-qq` that
    suppresses the summary, a crash before the summary is written: all of them
    give `killed-by=unknown`. Degrading to a WRONG name would be worse than
    degrading to no name, because the entire point of the field is to expose a
    kill that came from a module which should not be able to kill anything.
    """
    for raw in output.splitlines():
        match = _FAILURE_LINE.match(raw.strip())
        if match is not None:
            return match.group("node")
    return None


def failing_module(node_id: str | None) -> str | None:
    """The module half of a node id, in posix form, or None."""
    if node_id is None:
        return None
    return node_id.split("::", 1)[0].replace("\\", "/")


def _as_outcome(value: SuiteOutcome | int) -> SuiteOutcome:
    """Accept a bare exit code from a test double and degrade to no kill site."""
    if isinstance(value, SuiteOutcome):
        return value
    return SuiteOutcome(exit_code=int(value))


def pytest_suite_runner(repo_root: Path, suite: str = "tests") -> Callable[[Mutant], SuiteOutcome]:
    """The real classifier: non-zero exit means the mutant was KILLED.

    It also reads the first failing node id out of the output it already has, so
    that the report can say WHICH test killed a mutant. Nothing here re-runs
    pytest to find out.
    """

    def run(mutant: Mutant) -> SuiteOutcome:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            suite_argv(suite),
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return SuiteOutcome(exit_code=proc.returncode, node_id=parse_first_failure(output))

    return run


def run_campaign(
    target: Path,
    mutants: Sequence[Mutant],
    suite_runner: Callable[[Mutant], SuiteOutcome] | Callable[[Mutant], int],
    repo_root: Path | None = None,
    on_result: Callable[[MutantResult], None] | None = None,
) -> list[MutantResult]:
    """Apply each mutant in turn, classify it, and ALWAYS restore the target.

    Restore is in a `finally` and is verified by SHA256 against the bytes read
    before the first write. A KeyboardInterrupt mid-campaign leaves the tree
    clean and re-raises; a restore that does not verify raises `RestoreError`,
    because a tool that half-restores a source file and exits 0 is the worst
    available outcome.
    """
    root = REPO_ROOT if repo_root is None else Path(repo_root)
    path = Path(target)
    original = path.read_bytes()
    before = hashlib.sha256(original).hexdigest()

    results: list[MutantResult] = []
    try:
        for mutant in mutants:
            path.write_bytes(mutant.source.encode("utf-8"))
            purge_caches(root)
            outcome = _as_outcome(suite_runner(mutant))
            result = MutantResult(
                mutant=mutant,
                exit_code=outcome.exit_code,
                killed=outcome.exit_code != 0,
                node_id=outcome.node_id,
            )
            results.append(result)
            if on_result is not None:
                on_result(result)
    finally:
        path.write_bytes(original)
        purge_caches(root)
        after = hashlib.sha256(path.read_bytes()).hexdigest()
        if after != before:
            raise RestoreError(
                f"{path} was not restored: sha256 {before} before, {after} after. "
                f"The original bytes are lost from this process; recover from git."
            )
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def format_report(
    target: Path,
    digest: str,
    results: Sequence[MutantResult],
    unmutatable: Sequence[Unmutatable],
    suite: str,
) -> str:
    survivors = [result for result in results if not result.killed]
    false_kills = [result for result in results if result.false_kill]
    genuine = [result for result in results if result.killed and not result.false_kill]
    width = max((len(result.mutant.gate) for result in results), default=1)
    lines = [
        "gate mutation campaign",
        f"  when:    {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"  target:  {target}",
        f"  sha256:  {digest}",
        f"  suite:   {' '.join(suite_argv(suite)[1:])}",
        f"  mutants: {len(results)}",
        f"  unmutatable gates: {len(unmutatable)}",
    ]
    for entry in unmutatable:
        lines.append(f"    - {entry.gate} (line {entry.line}) has shape {entry.shape}, no mutation applied")
    lines.append("")
    for result in results:
        row = (
            f"  {result.verdict:<11}{result.mutant.gate:<{width}}  "
            # 16 wide, not 14: `except-reraise` is exactly 14 and ran into the
            # exit code with no space in the first corrected campaign.
            f"{result.mutant.label:<16}exit={result.exit_code}"
        )
        if result.killed:
            row += f"  killed-by={result.kill_site}"
        lines.append(row)
    lines.append("")
    lines.append(
        f"summary: {len(results)} mutants, {len(genuine)} killed, {len(survivors)} survived, "
        f"{len(false_kills)} false kills"
    )
    if false_kills:
        lines.append("")
        lines.append("!!! FALSE KILLS - THESE ARE NOT KILLS AND ARE NOT COUNTED AS KILLS !!!")
        lines.append(
            "each was killed by a module that grades the TARGET FILE'S SHAPE, so the suite "
            "went red over syntax and nothing was learned about whether any test drives the "
            "gate. Such a module must be named in SHAPE_GRADER_MODULES and excluded; if one "
            "reached a campaign, the exclusion list has a hole in it."
        )
        for result in false_kills:
            lines.append(f"  - {result.mutant.ident} killed-by={result.kill_site}")
    if survivors:
        # "the campaign suite", not "the suite". The campaign suite is the
        # application suite MINUS `EXCLUDED_MODULES`, so a survivor may still be
        # graded by a module that reads the target's SHAPE - and being graded on
        # shape is exactly not the same as being driven by a test, which is the
        # distinction this whole file exists to keep. Saying "the suite" here
        # would overclaim in the same direction the false kills did.
        lines.append("survivors - each names a gate no test in the campaign suite depends on:")
        for result in survivors:
            lines.append(f"  - {result.mutant.ident}")
    else:
        lines.append("no survivors")
    return "\n".join(lines) + "\n"


def _write_atomic(path: Path, text: str) -> None:
    """Atomic, and `write_bytes` so the LF survives Windows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(text.encode("ascii", "replace"))
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gate_mutation_runner",
        description=(
            "Neutralise each tagged gate in the responder's cycle in turn and run the "
            "application suite over it. A mutant that SURVIVES names a gate no test "
            "depends on."
        ),
        epilog=(
            "exit codes: 0 if every mutant was killed, 1 if any mutant survived. "
            "Gates whose tagged statement has no supported mutation shape are listed "
            "in the report header as unmutatable rather than skipped."
        ),
    )
    parser.add_argument("--target", default=None, help=f"file to mutate (default {RESPONDER})")
    parser.add_argument("--repo-root", default=None, help="tree to purge caches under and run the suite in")
    parser.add_argument("--function", default=FUNCTION, help=f"function holding the tags (default {FUNCTION})")
    parser.add_argument("--suite", default="tests", help="pytest target directory (default tests)")
    parser.add_argument("--gate", action="append", default=None, metavar="NAME", help="run one gate; repeatable")
    parser.add_argument("--report", default=None, help=f"report path (default {DEFAULT_REPORT})")
    parser.add_argument("--dry-run", action="store_true", help="print the mutant plan and touch nothing")
    parser.add_argument("--list", action="store_true", dest="list_tags", help="print the tags and touch nothing")
    return parser


def main(
    argv: Sequence[str] | None = None,
    suite_runner: Callable[[Mutant], SuiteOutcome] | Callable[[Mutant], int] | None = None,
    target: Path | None = None,
) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)

    path = Path(target) if target is not None else Path(args.target) if args.target else RESPONDER
    root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    report_path = Path(args.report) if args.report else DEFAULT_REPORT

    source = path.read_text(encoding="ascii")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    if args.list_tags:
        for tag in find_gate_tags(source):
            print(f"{tag.name}  line {tag.line}")
        return 0

    mutants, unmutatable = plan_mutants(source, args.function, args.gate)
    for entry in unmutatable:
        print(f"UNMUTATABLE  {entry.gate} (line {entry.line}) has shape {entry.shape}")

    if args.dry_run:
        for mutant in mutants:
            print(f"PLAN  {mutant.ident}  lines {mutant.first_line}-{mutant.last_line}")
        print(f"PLAN  {len(mutants)} mutants over {len({m.gate for m in mutants})} gates, nothing written")
        return 0

    if not mutants:
        print("no mutants planned - nothing to run")
        _write_atomic(report_path, format_report(path, digest, [], unmutatable, args.suite))
        return 0

    if suite_runner is None:
        # Only when a real campaign is about to run. A caller with its own
        # runner is not necessarily using `--ignore` at all.
        verify_exclusions(root)
    runner = suite_runner if suite_runner is not None else pytest_suite_runner(root, args.suite)
    index = {"n": 0}

    def announce(result: MutantResult) -> None:
        index["n"] += 1
        site = f" killed-by={result.kill_site}" if result.killed else ""
        print(
            f"[{index['n']}/{len(mutants)}] {result.verdict:<11}{result.mutant.ident} "
            f"exit={result.exit_code}{site}"
        )

    results = run_campaign(path, mutants, runner, repo_root=root, on_result=announce)
    report = format_report(path, digest, results, unmutatable, args.suite)
    _write_atomic(report_path, report)
    print(report)
    print(f"report written to {report_path}")
    return 1 if any(not result.killed or result.false_kill for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
