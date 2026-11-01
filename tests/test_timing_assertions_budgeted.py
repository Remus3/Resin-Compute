"""Every wall-clock bound in the test trees goes through fleet_test_guard.budget().

FLEET-9 (MAIN ORDER): a bound written for an idle box fails when another tree's
suite shares the CPU, and a failure nobody can act on trains readers to re-run.
`budget(seconds)` widens by the live suite-gate holder count, so the one question
this module asks is structural: does a bound that can FAIL a test by wall clock
go through it.

THE THREE SHAPES, each found in this tree before the guard existed:

  compare   an ordering comparison in an `assert` (or an `assertLess` family
            call) whose operand comes from a clock - directly, through a name
            assigned from one in the same function, or named elapsed / duration.
  deadline  `x = clock() + N`, with x later compared against a clock. A loop on
            it ends in an assert, so N is a bound even with no assert on the line.
  wait      `assert ev.wait(N)` / `if not ev.wait(N)`, where a False from the
            wait is the failure.

NOT COVERED, on purpose: a bare `timeout=` hang guard on a subprocess, a join or
an urlopen. Its failure is a wedge and most sit at 30 to 180 seconds. A site that
was tight enough to matter was converted by hand; the shape cannot tell them apart.

ALLOWED is keyed by (file, function, source text), never by line number, and an
entry that no longer matches a site reds, so the list cannot decay into a blanket.
"""
from __future__ import annotations

import ast
from pathlib import Path

import fleet_test_guard  # on sys.path via tests/conftest.py
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (REPO_ROOT / "tests", REPO_ROOT / "agents" / "pity_engine" / "tests")

CLOCK_ATTRS = frozenset({
    "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns",
})
#: Whole names only. A substring or a regex word boundary would also take
#: `_status_budget` or `within_budget`, neither of which is the guard's.
BUDGET_NAME = "budget"
ELAPSED_NAMES = frozenset({"elapsed", "duration", "took", "took_s", "elapsed_s", "duration_s"})
ORDERING = (ast.Lt, ast.LtE, ast.Gt, ast.GtE)
ASSERT_ORDERING = frozenset({"assertLess", "assertLessEqual", "assertGreater", "assertGreaterEqual"})
WAIT_ATTRS = frozenset({"wait"})

#: (repo-relative file, function, unparsed source) -> why it cannot fail by load.
ALLOWED: dict[tuple[str, str, str], str] = {
    ("tests/test_headless_env.py", "test_a_usage_limit_backs_off_and_the_next_cycle_spawns_nothing",
     "until > time.time()"):
        "the backoff stamp is written by the code under test well ahead of now; a stamp "
        "compared with now, not an act timed against a limit",
    ("tests/test_headless_env.py", "test_the_kit_writes_its_records_under_its_root_and_ends_idle",
     "starts[0] >= before"):
        "a lower bound taken before the act; load moves the stamp later, never earlier",
    ("tests/test_headless_jobs.py", "test_run_job_records_a_duration",
     "result.duration_ms >= 0.0"):
        "non-negative sanity on a monotonic difference; load only grows it",
    ("tests/test_headless_runner_checklist.py", "test_started_is_set_once_per_pass_and_carried_on_every_write",
     "before - 1 <= epoch <= after + 1"):
        "a bracket taken around the act: both ends move with the load, so it stays wide",
    ("tests/test_responder_checklist.py", "test_started_is_set_once_per_fire_and_carried_on_every_write",
     "before - 1 <= epoch <= after + 1"):
        "a bracket taken around the act: both ends move with the load, so it stays wide",
    ("tests/test_responder_inbox_v8.py", "test_r5_2_a_main_note_is_never_dropped_by_its_attempt_count",
     "later > 0"):
        "a count of fires, tainted only because the simulated times derive from t0",
    ("tests/test_responder_loop_breakers.py", "*",
     "rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, time.time()) >= set(rsp.OPTED_IN)"):
        "set containment; time.time() is an argument, not an operand",
    ("tests/test_responder_loop_breakers.py", "*",
     "rsp.senders_at_cap(rsp.DEFAULT_OUTBOUND, now) >= set(rsp.OPTED_IN)"):
        "set containment; now is an argument, not an operand",
    ("tests/test_headless_runner.py", "test_the_shutdown_flag_wakes_the_wait_early",
     "flag.wait(30)"):
        "the flag is already set, so the wait returns at once; False cannot come from load",
}


def _terminal(func: ast.expr) -> str | None:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


class _Scope:
    """One function's view: which local names came from a clock or a budget."""

    def __init__(self, node: ast.AST, clock_modules: frozenset[str]) -> None:
        self.node = node
        self.clock_modules = clock_modules
        self.clocked: set[str] = set()
        self.budgeted: set[str] = set()
        assigns = [
            n for n in self._own_nodes()
            if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None
        ]
        for _ in range(4):
            for assign in assigns:
                targets = assign.targets if isinstance(assign, ast.Assign) else [assign.target]
                names = [t.id for t in targets if isinstance(t, ast.Name)]
                if self.has_budget(assign.value):
                    self.budgeted.update(names)
                elif self.has_clock(assign.value):
                    self.clocked.update(names)

    def _own_nodes(self) -> list[ast.AST]:
        out: list[ast.AST] = []
        stack = list(ast.iter_child_nodes(self.node))
        while stack:
            node = stack.pop()
            out.append(node)
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                stack.extend(ast.iter_child_nodes(node))
        return out

    def is_clock_call(self, node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in CLOCK_ATTRS
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in self.clock_modules
        )

    def has_clock(self, expr: ast.AST) -> bool:
        for node in ast.walk(expr):
            if self.is_clock_call(node):
                return True
            if isinstance(node, ast.Name) and node.id in self.clocked:
                return True
        return False

    def has_budget(self, expr: ast.AST) -> bool:
        for node in ast.walk(expr):
            if isinstance(node, ast.Call) and _terminal(node.func) == BUDGET_NAME:
                return True
            if isinstance(node, ast.Name) and node.id in self.budgeted:
                return True
        return False

    def has_elapsed_name(self, expr: ast.AST) -> bool:
        for node in ast.walk(expr):
            if isinstance(node, ast.Name) and node.id in ELAPSED_NAMES:
                return True
            if isinstance(node, ast.Attribute) and node.attr in ELAPSED_NAMES:
                return True
            if isinstance(node, ast.Attribute) and node.attr == "duration_ms":
                return True
        return False

    def is_timed(self, expr: ast.AST) -> bool:
        return self.has_clock(expr) or self.has_elapsed_name(expr)


def _clock_modules(tree: ast.AST) -> frozenset[str]:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.asname or a.name for a in node.names if a.name == "time")
    return frozenset(found)


def _wait_timeout(call: ast.Call) -> ast.expr | None:
    if call.args:
        return call.args[0]
    for keyword in call.keywords:
        if keyword.arg == "timeout":
            return keyword.value
    return None


def _is_bounded_wait(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in WAIT_ATTRS
        and _wait_timeout(node) is not None
    )


def _scope_findings(scope: _Scope) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    nodes = scope._own_nodes()

    def _record(kind: str, node: ast.AST) -> None:
        found.append((kind, ast.unparse(node)))

    for node in nodes:
        if isinstance(node, ast.Assert):
            for sub in ast.walk(node.test):
                if (
                    isinstance(sub, ast.Compare)
                    and any(isinstance(op, ORDERING) for op in sub.ops)
                    and scope.is_timed(sub)
                    and not scope.has_budget(sub)
                ):
                    _record("compare", sub)
                if _is_bounded_wait(sub) and not scope.has_budget(_wait_timeout(sub)):
                    _record("wait", sub)
        elif isinstance(node, ast.Call) and _terminal(node.func) in ASSERT_ORDERING:
            if scope.is_timed(node) and not scope.has_budget(node):
                _record("compare", node)
        elif isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                test = test.operand
            if _is_bounded_wait(test) and not scope.has_budget(_wait_timeout(test)):
                _record("wait", test)

    # A deadline: x = clock() + N, unbudgeted, compared against a clock later.
    compared: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Compare) and any(isinstance(op, ORDERING) for op in node.ops):
            if scope.has_clock(node):
                compared.update(n.id for n in ast.walk(node) if isinstance(n, ast.Name))
    for node in nodes:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.BinOp)
            and isinstance(node.value.op, ast.Add)
            and (scope.is_clock_call(node.value.left) or scope.is_clock_call(node.value.right))
            and not scope.has_budget(node.value)
        ):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in compared:
                    _record("deadline", node)
    return found


def findings_in(source: str) -> list[tuple[str, str, str]]:
    """(kind, function, unparsed source) for every raw wall-clock bound in source."""
    tree = ast.parse(source)
    modules = _clock_modules(tree)
    rows: list[tuple[str, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for kind, text in _scope_findings(_Scope(node, modules)):
                rows.append((kind, node.name, text))
    return rows


def _corpus() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        files.extend(p for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts)
    return files


def _allowed(rel: str, function: str, text: str) -> tuple[str, str, str] | None:
    for key in ((rel, function, text), (rel, "*", text)):
        if key in ALLOWED:
            return key
    return None


def _census() -> tuple[list[str], set[tuple[str, str, str]]]:
    raw: list[str] = []
    used: set[tuple[str, str, str]] = set()
    for path in _corpus():
        rel = path.relative_to(REPO_ROOT).as_posix()
        for kind, function, text in findings_in(path.read_text(encoding="utf-8")):
            key = _allowed(rel, function, text)
            if key is None:
                raw.append(f"{rel}::{function} [{kind}] {text}")
            else:
                used.add(key)
    return raw, used


@pytest.fixture(scope="module")
def census() -> tuple[list[str], set[tuple[str, str, str]]]:
    return _census()


def test_every_wall_clock_bound_goes_through_the_budget(census) -> None:
    raw, _used = census
    assert raw == [], (
        "a raw wall-clock bound fails when another suite shares the CPU. Wrap N in "
        "fleet_test_guard.budget(N), or add it to ALLOWED with the reason load cannot "
        f"fail it: {raw}"
    )


def test_no_allowed_entry_outlives_its_site(census) -> None:
    _raw, used = census
    stale = sorted(set(ALLOWED) - used)
    assert stale == [], f"ALLOWED names a site that no longer exists: {stale}"


def test_the_scan_reaches_both_trees_and_sees_the_budgeted_sites() -> None:
    """A walk that read nothing would pass the census with an empty list."""
    corpus = _corpus()
    assert any(p.parent == SCAN_ROOTS[0] for p in corpus)
    assert any(p.is_relative_to(SCAN_ROOTS[1]) for p in corpus)
    this = Path(__file__).resolve()
    assert this in [p.resolve() for p in corpus]
    budgeted = sum(
        p.read_text(encoding="utf-8").count("fleet_test_guard.budget(")
        for p in corpus if p.resolve() != this
    )
    assert budgeted > 0, "no budgeted site found: the corpus is not the test tree"


@pytest.mark.parametrize(
    ("kind", "body"),
    [
        ("compare", "t0 = time.monotonic()\n    act()\n    assert time.monotonic() - t0 < 2.0"),
        ("compare", "start = time.time()\n    act()\n    took = time.time() - start\n    assert took < 2.0"),
        ("compare", "assert (\n        time.perf_counter() - T\n        < 2.0\n    )"),
        ("compare", "elapsed = run()\n    assert elapsed < 2.0"),
        ("compare", "assert fired.elapsed <= 2.0"),
        ("compare", "t0 = time.time()\n    self.assertLess(time.time() - t0, 2.0)"),
        ("deadline", "end = time.monotonic() + 20.0\n    while time.monotonic() < end:\n        poll()"),
        ("deadline", "end = time.time() + 5\n    assert time.time() < end or done()"),
        ("wait", "assert ev.wait(5)"),
        ("wait", "assert ev.wait(timeout=5.0)"),
        ("wait", "if not ev.wait(30.0):\n        pytest.fail('x')"),
    ],
)
def test_the_detector_fires_on_every_raw_shape(kind: str, body: str) -> None:
    source = f"import time\n\ndef test_x(self=None):\n    {body}\n"
    assert kind in [row[0] for row in findings_in(source)], source


@pytest.mark.parametrize(
    "body",
    [
        "t0 = time.monotonic()\n    assert time.monotonic() - t0 < fleet_test_guard.budget(2.0)",
        "elapsed = run()\n    assert elapsed < SMALL + fleet_test_guard.budget(2.0)",
        "limit = fleet_test_guard.budget(2.0)\n    t0 = time.monotonic()\n    assert time.monotonic() - t0 < limit",
        "end = time.monotonic() + fleet_test_guard.budget(20.0)\n    while time.monotonic() < end:\n        poll()",
        "assert ev.wait(fleet_test_guard.budget(5))",
        "if not ev.wait(timeout=fleet_test_guard.budget(30.0)):\n        pytest.fail('x')",
        # Legitimate neighbours: no clock, or the compare fails nothing.
        "assert len(rows) < 2.0",
        "assert budget_left < 2.0",
        "now = time.time()\n    write_stamp(now + 3600)",
        "ev.wait(5)",
        "worker.join(5)",
        "t0 = time.time()\n    while cond(t0):\n        poll()",
    ],
)
def test_the_detector_leaves_the_neighbours_alone(body: str) -> None:
    source = f"import time\n\ndef test_x():\n    {body}\n"
    assert findings_in(source) == [], source


def test_a_lookalike_budget_does_not_count_as_the_budget() -> None:
    """Terminal name only: `_status_budget` is a domain function, not the guard's."""
    source = (
        "import time\n\ndef test_x():\n"
        "    t0 = time.time()\n"
        "    assert time.time() - t0 < rsp._status_budget(cap, 1.0)\n"
    )
    assert [row[0] for row in findings_in(source)] == ["compare"]


# ---------------------------------------------------------------------------
# The guard's extra_ignore: concurrent live writers are not test leaks
# ---------------------------------------------------------------------------


def _live_writer_ignores() -> tuple[str, ...]:
    """Read from the source: importing tests/conftest.py a second time re-installs."""
    tree = ast.parse((REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "LIVE_WRITER_IGNORES"
        ):
            return tuple(ast.literal_eval(node.value))
    raise AssertionError("tests/conftest.py no longer declares LIVE_WRITER_IGNORES")


def _plant(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x\n")


def test_conftest_hands_the_live_writer_list_to_the_guard() -> None:
    tree = ast.parse((REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8"))
    wired = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _terminal(node.func) == "install"
        and any(
            kw.arg == "extra_ignore"
            and isinstance(kw.value, ast.Name)
            and kw.value.id == "LIVE_WRITER_IGNORES"
            for kw in node.keywords
        )
    ]
    assert len(wired) == 1, "the guard is not told about the concurrent live writers"


@pytest.mark.parametrize(
    "rel",
    [
        "ops/loop/control/inbox_pending_orders.json",
        "ops/loop/control/headless_budget.reset-2026-11-01.json",
        "ops/loop/control/scratch/suite.txt",
        "ops/loop/control/scratch/kitv24/msg.txt",
    ],
)
def test_a_live_writer_file_does_not_read_as_a_leak(tmp_path: Path, rel: str) -> None:
    ignore = fleet_test_guard.IGNORE + _live_writer_ignores()
    before = fleet_test_guard.snapshot(tmp_path, ignore=ignore)
    _plant(tmp_path, rel)
    after = fleet_test_guard.snapshot(tmp_path, ignore=ignore)
    assert fleet_test_guard.compare(before, after) == ([], [], [])


@pytest.mark.parametrize(
    "rel",
    [
        "ops/loop/control/inbox_pending_orders.json.bak",
        "ops/loop/control/roots_map_probe.json",
        "ops/loop/control/s83b_lead.txt",
        "ops/loop/control/scratchpad/suite.txt",
        "moon_sync_outbox/2026-11-01-note.txt",
    ],
)
def test_a_neighbour_of_the_live_writers_is_still_a_leak(tmp_path: Path, rel: str) -> None:
    """The sweep's second guard: the ignore list did not swallow the directory."""
    ignore = fleet_test_guard.IGNORE + _live_writer_ignores()
    before = fleet_test_guard.snapshot(tmp_path, ignore=ignore)
    _plant(tmp_path, rel)
    after = fleet_test_guard.snapshot(tmp_path, ignore=ignore)
    assert fleet_test_guard.compare(before, after) == ([], [], [rel])
