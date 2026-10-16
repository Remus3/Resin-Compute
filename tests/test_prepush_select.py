"""Arms for `scripts/prepush_select.py`, the pre-push test selector.

WHY IT EXISTS (MAIN 2246 ORDER section 2, PERF-AUDIT item 1). The pre-push
hook ran both whole suites serially on every push - about 230 s, and a
low-memory run went red. The hook now runs ruff, the engine suite, and only
the application modules a push can plausibly affect. The whole application
suite still runs in CI and on the nightly schedule.

THE MAPPING, kept simple and deterministic on purpose:

  - a changed `tests/test_*.py` runs itself;
  - any other changed path maps to every `tests/test_*.py` that MENTIONS it -
    its repo path, its path without `.py`, its dotted module, its basename,
    or an `import <stem>` / `from <stem> import` line;
  - plumbing modules (tests/_markers.py PLUMBING) reached only through that
    mapping are dropped unless the diff touches a plumbing root;
  - the modules pytest's own cache records as last-failed are always added;
  - no upstream, a selector error, a diff of more than MAX_CHANGED paths, or a
    change to a FULL trigger (a conftest, pytest.ini, the marker registry,
    the dev pins) falls back to the FULL application suite.

Every arm here feeds `select()` hand-built inputs, so none of them needs git;
one end-to-end arm drives the CLI against a throwaway repository.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import prepush_select as sel
from tests._markers import PLUMBING

REPO_ROOT = Path(__file__).resolve().parent.parent


def _grep_from(table: dict[str, set[str]]):
    """A fake grep: module -> the needles its text contains."""

    def grep(needles):
        wanted = set(needles)
        return {mod for mod, has in table.items() if has & wanted}

    return grep


def _exists(*paths: str):
    present = set(paths)
    return lambda path: path in present


def _select(changed, table=None, existing=(), plumbing=frozenset(), last_failed=()):
    return sel.select(
        changed,
        grep=_grep_from(table or {}),
        exists=_exists(*existing),
        plumbing=plumbing,
        last_failed=last_failed,
    )


# ---------------------------------------------------------------------------
# needles
# ---------------------------------------------------------------------------


def test_a_python_source_yields_its_path_module_and_import_forms():
    needles = set(sel.needles_for("core/atomic_io.py"))
    assert {
        "core/atomic_io.py",
        "core/atomic_io",
        "core.atomic_io",
        "atomic_io.py",
        "import atomic_io",
        "from atomic_io import",
    } <= needles


def test_a_generic_basename_is_never_a_needle():
    """`__init__.py` is in every package; as a needle it would select everything."""
    needles = set(sel.needles_for("core/__init__.py"))
    assert "__init__.py" not in needles
    assert "core/__init__.py" in needles
    assert "core" not in needles, "a package's bare dotted name is too broad a needle"


def test_a_non_python_path_yields_its_path_and_basename():
    assert set(sel.needles_for(".githooks/pre-push")) == {".githooks/pre-push", "pre-push"}


# ---------------------------------------------------------------------------
# select(): the three modes
# ---------------------------------------------------------------------------


def test_a_changed_test_module_runs_itself():
    got = _select(["tests/test_core_resin.py"], existing=["tests/test_core_resin.py"])
    assert got.mode == sel.SELECT
    assert got.modules == ("tests/test_core_resin.py",)


def test_a_changed_source_maps_to_the_modules_that_mention_it():
    table = {
        "tests/test_core_resin.py": {"core/resin.py", "core.resin"},
        "tests/test_core_ledger.py": {"core.ledger"},
    }
    got = _select(["core/resin.py"], table=table)
    assert got.mode == sel.SELECT
    assert got.modules == ("tests/test_core_resin.py",), (
        "non-vacuity in both directions: the mentioning module is in and the "
        "neighbour that mentions something else is out"
    )


def test_a_deleted_test_module_is_not_handed_to_pytest():
    got = _select(["tests/test_gone.py"], existing=[])
    assert got.mode == sel.NONE
    assert got.modules == ()


@pytest.mark.parametrize(
    "trigger",
    sorted(sel.FULL_TRIGGERS),
)
def test_every_full_trigger_falls_back_to_the_whole_suite(trigger):
    got = _select(["core/resin.py", trigger])
    assert got.mode == sel.FULL
    assert trigger in got.reason


@pytest.mark.parametrize("declaration", ["requirements.in", "requirements-dev.in"])
def test_a_requirements_declaration_forces_the_whole_suite(declaration):
    """Named literally, not drawn from FULL_TRIGGERS, so dropping either .in
    from the set reds here (MAIN ORDER 1925 item e)."""
    got = _select(["core/resin.py", declaration])
    assert got.mode == sel.FULL
    assert declaration in got.reason


def test_a_huge_diff_falls_back_to_the_whole_suite():
    changed = [f"core/f{i}.py" for i in range(sel.MAX_CHANGED + 1)]
    assert _select(changed).mode == sel.FULL


def test_a_diff_at_the_bound_is_still_selected():
    """Surviving neighbour of the arm above: the bound is not off by one."""
    changed = [f"core/f{i}.py" for i in range(sel.MAX_CHANGED)]
    assert _select(changed).mode == sel.NONE


def test_a_docs_only_diff_with_no_mention_selects_nothing():
    got = _select(["docs/LEDGER.md"])
    assert got.mode == sel.NONE
    assert "1 changed path" in got.reason


def test_an_empty_diff_selects_nothing():
    assert _select([]).mode == sel.NONE


# ---------------------------------------------------------------------------
# select(): plumbing
# ---------------------------------------------------------------------------


def test_a_plumbing_module_reached_by_mapping_is_dropped_for_a_product_diff():
    table = {
        "tests/test_core_atomic_io.py": {"core/atomic_io.py"},
        "tests/test_hook_gate.py": {"core/atomic_io.py"},
    }
    got = _select(
        ["core/atomic_io.py"],
        table=table,
        plumbing=frozenset({"tests/test_hook_gate.py"}),
    )
    assert got.modules == ("tests/test_core_atomic_io.py",)


@pytest.mark.parametrize("root", sel.PLUMBING_ROOTS)
def test_a_plumbing_root_in_the_diff_keeps_the_plumbing_modules(root):
    changed = f"{root}thing.py"
    table = {"tests/test_hook_gate.py": {changed}}
    got = _select([changed], table=table, plumbing=frozenset({"tests/test_hook_gate.py"}))
    assert got.modules == ("tests/test_hook_gate.py",)


def test_a_changed_plumbing_test_runs_itself_even_for_a_product_diff():
    got = _select(
        ["core/resin.py", "tests/test_hook_gate.py"],
        existing=["tests/test_hook_gate.py"],
        plumbing=frozenset({"tests/test_hook_gate.py"}),
    )
    assert "tests/test_hook_gate.py" in got.modules


# ---------------------------------------------------------------------------
# select(): last-failed
# ---------------------------------------------------------------------------


def test_last_failed_modules_are_always_added():
    got = _select(
        ["docs/LEDGER.md"],
        existing=["tests/test_core_ledger.py"],
        last_failed=["tests/test_core_ledger.py"],
    )
    assert got.mode == sel.SELECT
    assert got.modules == ("tests/test_core_ledger.py",)


def test_a_last_failed_module_that_no_longer_exists_is_dropped():
    got = _select(["docs/LEDGER.md"], last_failed=["tests/test_gone.py"])
    assert got.mode == sel.NONE


# ---------------------------------------------------------------------------
# select(): CI-only modules (MAIN 2246 ORDER s2 item 2c - the 30 s target)
# ---------------------------------------------------------------------------

_CI_ONLY_MOD = "tests/test_hook_gate.py"
_CI_ONLY_TABLE = {
    _CI_ONLY_MOD: {"tools/precommit_gate.py"},
    "tests/test_precommit_gate_corpus.py": {"tools/precommit_gate.py"},
}


def _select_ci_only(changed, existing=(), last_failed=()):
    return sel.select(
        changed,
        grep=_grep_from(_CI_ONLY_TABLE),
        exists=_exists(*existing),
        plumbing=frozenset(),
        last_failed=last_failed,
        ci_only=frozenset({_CI_ONLY_MOD}),
    )


def test_a_ci_only_module_reached_by_mapping_is_dropped_and_its_neighbour_survives():
    got = _select_ci_only(["tools/precommit_gate.py"])
    assert got.mode == sel.SELECT
    assert got.modules == ("tests/test_precommit_gate_corpus.py",)
    assert "1 CI-only deferred" in got.reason


def test_without_a_ci_only_set_the_same_mapping_keeps_the_module():
    # Non-vacuity: the drop above is the ci_only argument's doing, not the table's.
    got = _select(["tools/precommit_gate.py"], table=_CI_ONLY_TABLE)
    assert _CI_ONLY_MOD in got.modules
    assert "CI-only" not in got.reason


def test_a_changed_ci_only_test_still_runs_itself():
    got = _select_ci_only(["tools/precommit_gate.py", _CI_ONLY_MOD], existing=[_CI_ONLY_MOD])
    assert _CI_ONLY_MOD in got.modules


def test_a_last_failed_ci_only_module_still_runs():
    got = _select_ci_only(
        ["tools/precommit_gate.py"], existing=[_CI_ONLY_MOD], last_failed=[_CI_ONLY_MOD]
    )
    assert _CI_ONLY_MOD in got.modules


def test_a_diff_mapping_only_to_ci_only_modules_selects_nothing():
    got = sel.select(
        ["tools/precommit_gate.py"],
        grep=_grep_from({_CI_ONLY_MOD: {"tools/precommit_gate.py"}}),
        exists=_exists(),
        plumbing=frozenset(),
        last_failed=(),
        ci_only=frozenset({_CI_ONLY_MOD}),
    )
    assert got.mode == sel.NONE
    assert "1 CI-only deferred" in got.reason


#: The fast, high-signal tree-wide guards the pre-push gate must keep running:
#: the glyph gate's corpus, the sibling-name sweep, interpreter pinning, the
#: fleet-kit pin, the secret-literal and machine-identity sweeps, line endings.
_KEEP_LOCAL = frozenset(
    {
        "tests/test_precommit_gate_corpus.py",
        "tests/test_no_sibling_names.py",
        "tests/test_interpreter_pinning.py",
        "tests/test_fleet_kit.py",
        "tests/test_no_secret_literals.py",
        "tests/test_machine_identity.py",
        "tests/test_line_endings.py",
        "tests/test_prepush_select.py",
    }
)


def test_the_shipped_ci_only_set_names_real_modules_and_spares_the_fast_guards():
    assert sel.CI_ONLY, "non-vacuity: an empty set would make the deferral a no-op"
    for module in sel.CI_ONLY:
        assert sel._is_test_module(module), module
        assert (REPO_ROOT / module).is_file(), f"CI_ONLY names a missing module: {module}"
    assert not (sel.CI_ONLY & _KEEP_LOCAL), sorted(sel.CI_ONLY & _KEEP_LOCAL)


def test_ci_still_runs_every_ci_only_module_the_hook_would_have_mapped():
    # A plumbing module in CI_ONLY is mapped only when a plumbing root changed,
    # and then ci_mark_for is "" (every module runs in CI). A product module in
    # CI_ONLY is never deselected by the "not plumbing" mark at all.
    assert sel.ci_mark_for(["core/x.py"]) == "not plumbing"
    for module in sel.CI_ONLY:
        if module not in PLUMBING:
            continue  # "not plumbing" keeps it on every CI push
        for root in sel.PLUMBING_ROOTS:
            assert sel.ci_mark_for([f"{root}x.py"]) == "", (module, root)


def _ci_cancel_in_progress(text: str) -> str:
    """The workflow-level `concurrency: cancel-in-progress:` value of ci.yml."""
    lines = text.splitlines()
    start = lines.index("concurrency:")
    for line in lines[start + 1:]:
        if line and not line.startswith(" "):
            break
        key, _, value = line.strip().partition(":")
        if key == "cancel-in-progress":
            return value.strip()
    raise AssertionError("ci.yml concurrency block has no cancel-in-progress key")


#: The only accepted spelling: a push run is never cancelled; a superseded
#: pull-request or dispatch run still is.
_PUSH_NEVER_CANCELLED = "${{ github.event_name != 'push' }}"


def test_a_push_run_in_ci_is_never_cancelled_so_ci_only_modules_always_run():
    # Adversary counter-example against 64d05a7: push A breaks a hook, the hook
    # now defers test_hook_gate, push B (core/ only) cancels A's CI run and
    # diffs from A, so ci_mark_for gives "not plumbing" and the PLUMBING
    # CI_ONLY modules never run until the nightly. A push run must finish.
    text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="ascii")
    assert _ci_cancel_in_progress(text) == _PUSH_NEVER_CANCELLED


@pytest.mark.parametrize("value", ["true", "${{ true }}", "${{ github.event_name == 'push' }}"])
def test_the_cancel_parser_reports_a_cancellable_push_run(value: str):
    # Non-vacuity: the arm above reads the real key, and would see a regression.
    text = f"on: push\nconcurrency:\n  group: g\n  cancel-in-progress: {value}\njobs: {{}}\n"
    assert _ci_cancel_in_progress(text) != _PUSH_NEVER_CANCELLED


def test_the_cli_defers_a_shipped_ci_only_module(tmp_path: Path):
    from tests.conftest import require_git_repository

    require_git_repository()
    root = tmp_path / "r"
    (root / "tests").mkdir(parents=True)
    (root / "core").mkdir()
    (root / "core" / "thing.py").write_text("X = 1\n", encoding="ascii", newline="\n")
    deferred = sorted(sel.CI_ONLY)[0]
    for module in (deferred, "tests/test_thing.py"):
        (root / module).write_text("# core/thing.py\n", encoding="ascii", newline="\n")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    base = _git(root, "rev-parse", "HEAD").strip()
    (root / "core" / "thing.py").write_text("X = 2\n", encoding="ascii", newline="\n")
    _git(root, "commit", "-q", "-am", "change")
    mode, reason, modules = _cli(root, "--base", base)
    assert mode == sel.SELECT
    assert modules == "tests/test_thing.py"
    assert "CI-only deferred" in reason


def test_the_cache_reader_keeps_app_suite_modules_only(tmp_path: Path):
    cache = tmp_path / "lastfailed"
    cache.write_text(
        json.dumps(
            {
                "tests/test_core_resin.py::test_x": True,
                "tests/test_core_resin.py::test_y[1]": True,
                "agents/pity_engine/tests/test_pity_curves.py::test_z": True,
                "tests/test_core_ledger.py": True,
            }
        ),
        encoding="utf-8",
    )
    assert sel.last_failed_modules(cache) == {
        "tests/test_core_resin.py",
        "tests/test_core_ledger.py",
    }


@pytest.mark.parametrize("body", ["", "not json", "[1, 2]", '{"tests/test_a.py": true'])
def test_an_absent_or_corrupt_cache_contributes_nothing(tmp_path: Path, body: str):
    cache = tmp_path / "lastfailed"
    if body:
        cache.write_text(body, encoding="utf-8")
    assert sel.last_failed_modules(cache) == set()


# ---------------------------------------------------------------------------
# render(): the three-line protocol the hook reads
# ---------------------------------------------------------------------------


def test_render_is_four_lines_mode_reason_modules_engine():
    out = sel.render(sel.Selection(sel.SELECT, "why", ("tests/test_a.py", "tests/test_b.py")))
    assert out.split("\n") == [
        sel.SELECT, "why", "tests/test_a.py,tests/test_b.py", sel.ENGINE_RUN
    ]
    skipped = sel.Selection(sel.NONE, "w", (), sel.ENGINE_SKIP, "no path reaches it")
    assert sel.render(skipped).split("\n")[3] == f"{sel.ENGINE_SKIP} no path reaches it"


def test_a_path_with_whitespace_or_a_comma_forces_full():
    """The hook splits the module line on commas; such a path cannot survive it."""
    for bad in ("tests/test_a b.py", "tests/test_a,b.py"):
        got = _select([bad], existing=[bad])
        assert got.mode == sel.FULL, bad


# ---------------------------------------------------------------------------
# The real plumbing registry is what the hook consumes
# ---------------------------------------------------------------------------


def test_main_reads_the_shipped_plumbing_registry():
    assert sel.load_plumbing() == PLUMBING
    assert PLUMBING, "non-vacuity: an empty registry would make the filter a no-op"


# ---------------------------------------------------------------------------
# End to end: the CLI against a throwaway repository
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
    )
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, env=env
    ).stdout


def _cli(repo: Path, *args: str) -> list[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    out = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "prepush_select.py"), "--root", str(repo), *args],
        capture_output=True, text=True, check=True, env=env,
    ).stdout
    return out.removesuffix("\n").split("\n")[:3]


def _cli_lines(repo: Path, *args: str) -> list[str]:
    """Every line the CLI printed, the engine line included."""
    return _cli_raw(repo, *args).removesuffix("\n").split("\n")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    from tests.conftest import require_git_repository

    require_git_repository()
    root = tmp_path / "r"
    (root / "tests").mkdir(parents=True)
    (root / "core").mkdir()
    (root / "core" / "thing.py").write_text("X = 1\n", encoding="ascii", newline="\n")
    (root / "tests" / "test_thing.py").write_text(
        "from core.thing import X\n", encoding="ascii", newline="\n"
    )
    (root / "tests" / "test_other.py").write_text("Y = 2\n", encoding="ascii", newline="\n")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return root


def test_cli_selects_by_diff_against_a_base(repo: Path):
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "core" / "thing.py").write_text("X = 2\n", encoding="ascii", newline="\n")
    _git(repo, "commit", "-q", "-am", "change")
    mode, _reason, modules = _cli(repo, "--base", base)
    assert mode == sel.SELECT
    assert modules == "tests/test_thing.py"


def test_cli_without_an_upstream_falls_back_to_full(repo: Path):
    mode, reason, _ = _cli(repo)
    assert mode == sel.FULL
    assert "upstream" in reason


def test_cli_with_an_all_zero_base_falls_back_to_full(repo: Path):
    mode, _reason, _ = _cli(repo, "--base", "0" * 40)
    assert mode == sel.FULL


# ---------------------------------------------------------------------------
# --ci-mark: the marker expression ci.yml's push and pull-request jobs use
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        (["core/resin.py"], "not plumbing"),
        (["docs/LEDGER.md", "engines/x.py"], "not plumbing"),
        (["tools/precommit_gate.py"], ""),
        (["core/resin.py", ".github/workflows/ci.yml"], ""),
        (["tests/conftest.py"], ""),
        (["pytest.ini"], ""),
        ([], "not plumbing"),
    ],
)
def test_ci_mark_runs_plumbing_only_when_a_plumbing_root_or_trigger_changed(changed, expected):
    assert sel.ci_mark_for(changed) == expected


def test_ci_mark_runs_everything_for_a_huge_diff():
    assert sel.ci_mark_for([f"core/f{i}.py" for i in range(sel.MAX_CHANGED + 1)]) == ""


def _cli_raw(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "prepush_select.py"), "--root", str(repo), *args],
        capture_output=True, text=True, check=True, env=env,
    ).stdout


def test_cli_ci_mark_without_a_base_runs_everything(repo: Path):
    assert _cli_raw(repo, "--ci-mark") == "\n"


def test_cli_ci_mark_with_a_product_only_diff_deselects_plumbing(repo: Path):
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "core" / "thing.py").write_text("X = 3\n", encoding="ascii", newline="\n")
    _git(repo, "commit", "-q", "-am", "product")
    assert _cli_raw(repo, "--ci-mark", "--base", base) == "not plumbing\n"


def test_cli_ci_mark_with_a_plumbing_diff_runs_everything(repo: Path):
    base = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "tools").mkdir()
    (repo / "tools" / "t.py").write_text("Z = 1\n", encoding="ascii", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "plumbing")
    assert _cli_raw(repo, "--ci-mark", "--base", base) == "\n"


# ---------------------------------------------------------------------------
# The engine suite runs only when the push can reach it (0i 2c, the 30 s
# target). Profiled 2026-10-12 on this host (Python 3.14), a one-file plumbing
# push: app selection 24.2 s, engine suite 9.4 s, everything else under 1 s.
# The engine suite is a pure function of its own import closure plus the
# pytest configuration, so a push that changes neither cannot change its
# verdict. CI (.github/workflows/ci.yml "Engine suite") still runs it on
# every push.
# ---------------------------------------------------------------------------

_CLOSURE = frozenset(
    {
        "agents/__init__.py",
        "agents/pity_engine/__init__.py",
        "agents/pity_engine/markov.py",
        "conftest.py",
        "core/__init__.py",
        "core/types.py",
        "ops/__init__.py",
        "ops/health.py",
    }
)
_TOP_NAMES = frozenset({"json", "pytest"})  # external names only


def _engine(changed, last_failed=()):
    return sel.engine_decision(
        changed, closure=_CLOSURE, top_names=_TOP_NAMES, last_failed=last_failed
    )


@pytest.mark.parametrize(
    "changed",
    [
        ["tools/precommit_gate.py"],
        ["docs/LEDGER.md"],
        ["tests/test_prepush_select.py"],
        ["headless/runner.py", "scripts/watch_inbox.py", ".github/workflows/ci.yml"],
        ["engines/scheduler.py"],
        ["core/resin.py"],  # a module beside the closure, never imported by it
        ["ops/fleet_kit/fleet_claims.py"],  # an in-repo package, not a shadow
        [],
    ],
)
def test_a_push_outside_the_engine_closure_skips_the_engine_suite(changed):
    verdict, reason = _engine(changed)
    assert verdict == sel.ENGINE_SKIP, reason
    assert "CI" in reason


@pytest.mark.parametrize(
    "path",
    [
        "agents/pity_engine/markov.py",  # in the closure
        "agents/pity_engine/CHANGELOG.md",  # anything under agents/
        "agents/conftest.py",  # a conftest pytest loads on the way down
        "agents/pity_engine/tests/test_new.py",  # a new engine test
        "core/types.py",  # imported by the engine
        "ops/health.py",  # reached only through the root conftest's try-import
        "core/fixture.json",  # a data file beside a closure module
        "conftest.py",  # root conftest, FULL trigger and closure
        "pytest.ini",  # pytest configuration
        "requirements-dev.txt",  # the pytest that runs it
        "sitecustomize.py",  # any root-level module is on sys.path[0]
        "json.py",  # would shadow a module the closure imports
        "pytest/__init__.py",  # same, as a package
    ],
)
def test_a_push_reaching_the_engine_runs_it(path):
    verdict, reason = _engine(["tools/precommit_gate.py", path])
    assert verdict == sel.ENGINE_RUN, (path, reason)


def test_a_huge_diff_runs_the_engine_suite():
    verdict, _ = _engine([f"tools/f{i}.py" for i in range(sel.MAX_CHANGED + 1)])
    assert verdict == sel.ENGINE_RUN


def test_a_last_failed_engine_test_runs_the_engine_suite():
    verdict, reason = _engine(
        ["tools/precommit_gate.py"],
        last_failed=["agents/pity_engine/tests/test_markov.py"],
    )
    assert verdict == sel.ENGINE_RUN
    assert "last-failed" in reason


def test_the_real_engine_closure_holds_its_imports_and_spares_plumbing():
    """Non-vacuity on the shipped tree: the walker sees nested and try-imports
    (ops/health.py is reached only through the root conftest's try-import),
    and a plumbing file the engine never imports stays outside."""
    closure, top_names = sel.engine_closure(REPO_ROOT)
    for must in (
        "agents/pity_engine/__init__.py",
        "agents/pity_engine/markov.py",
        "agents/pity_engine/tests/test_markov.py",
        "core/types.py",
        "core/ports.py",
        "conftest.py",
        "ops/health.py",
        "ops/loop/slots.py",
    ):
        assert must in closure, must
    for spared in ("tools/precommit_gate.py", "headless/runner.py", "scripts/prepush_select.py"):
        assert spared not in closure, spared
    assert {"pytest", "json"} <= top_names
    assert not {"core", "ops", "agents"} & top_names, "repo packages are not shadows"


def test_the_closure_walker_follows_relative_and_from_imports(tmp_path: Path):
    root = tmp_path / "r"
    for rel, body in {
        "conftest.py": "import pkg\n",
        "pkg/__init__.py": "from . import a\n",
        "pkg/a.py": "from .sub import b\ndef f():\n    from other import thing\n",
        "pkg/sub/__init__.py": "",
        "pkg/sub/b.py": "import json\n",
        "other.py": "thing = 1\n",
        "unrelated.py": "import os\n",
        "agents/pity_engine/__init__.py": "import pkg.a\n",
        "agents/__init__.py": "",
    }.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="ascii", newline="\n")
    closure, top_names = sel.engine_closure(root)
    assert {
        "conftest.py", "pkg/__init__.py", "pkg/a.py", "pkg/sub/__init__.py",
        "pkg/sub/b.py", "other.py", "agents/__init__.py", "agents/pity_engine/__init__.py",
    } <= closure
    assert "unrelated.py" not in closure
    assert "json" in top_names


@pytest.fixture()
def repo_with_engine(repo: Path) -> Path:
    (repo / "agents" / "pity_engine").mkdir(parents=True)
    (repo / "agents" / "__init__.py").write_text("", encoding="ascii", newline="\n")
    (repo / "agents" / "pity_engine" / "__init__.py").write_text(
        "from core.thing import X\n", encoding="ascii", newline="\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "engine")
    return repo


def _commit_tools_change(repo: Path) -> None:
    (repo / "tools").mkdir()
    (repo / "tools" / "t.py").write_text("Z = 1\n", encoding="ascii", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "plumbing")


def test_cli_skips_the_engine_for_a_push_outside_its_closure(repo_with_engine: Path):
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    _commit_tools_change(repo_with_engine)
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(f"{sel.ENGINE_SKIP} "), lines


def test_an_unparseable_closure_file_runs_the_engine_suite(repo_with_engine: Path):
    """The pair of the arm above: same tools/ push, but a closure module the
    walker cannot parse. The verdict must fall back to RUN, never SKIP."""
    (repo_with_engine / "core" / "thing.py").write_text("def (\n", encoding="ascii", newline="\n")
    _git(repo_with_engine, "commit", "-q", "-am", "broken")
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    _commit_tools_change(repo_with_engine)
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(sel.ENGINE_RUN), lines


def test_cli_runs_the_engine_when_its_import_changed(repo_with_engine: Path):
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    (repo_with_engine / "core" / "thing.py").write_text("X = 9\n", encoding="ascii", newline="\n")
    _git(repo_with_engine, "commit", "-q", "-am", "product")
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(sel.ENGINE_RUN), lines


def test_cli_runs_the_engine_without_a_base(repo_with_engine: Path):
    assert _cli_lines(repo_with_engine)[3].startswith(sel.ENGINE_RUN)


# ---------------------------------------------------------------------------
# The hook honours the engine line, and ONLY a literal SKIP token skips
# ---------------------------------------------------------------------------

_HOOK_STUB = (
    "#!/bin/sh\n"
    "# Stub interpreter: claims every import, prints the canned selection,\n"
    "# logs every pytest invocation and runs nothing.\n"
    'case "$*" in\n'
    '  *prepush_select.py*) cat "$RSC_TEST_CANNED"; exit 0 ;;\n'
    '  *"-m pytest"*) printf \'%s\\n\' "$*" >> "$RSC_TEST_LOG"; exit 0 ;;\n'
    "esac\n"
    "exit 0\n"
)


def _hook_pytest_calls(tmp_path: Path, canned: str) -> list[str]:
    from tests.test_hook_interpreter import _run_prepush

    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for name in ("python3", "python", "py"):
        (stubs / name).write_text(_HOOK_STUB, encoding="ascii", newline="\n")
        (stubs / name).chmod(0o755)
    canned_file = tmp_path / "canned.txt"
    canned_file.write_text(canned, encoding="ascii", newline="\n")
    log = tmp_path / "pytest.log"
    log.write_text("", encoding="ascii", newline="\n")
    result = _run_prepush(
        stubs,
        env={"RSC_TEST_CANNED": canned_file.as_posix(), "RSC_TEST_LOG": log.as_posix()},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "pre-push: OK" in result.stdout, result.stdout
    return log.read_text(encoding="ascii").splitlines()


def test_the_hook_skips_the_engine_suite_on_a_skip_line(tmp_path: Path):
    calls = _hook_pytest_calls(tmp_path, "FULL\nwhy\n\nSKIP no path reaches it\n")
    assert [c for c in calls if " tests " in f" {c} "], (
        "non-vacuity: the application suite must still have been invoked", calls
    )
    assert not [c for c in calls if "agents/pity_engine" in c], calls


@pytest.mark.parametrize(
    "canned",
    [
        "FULL\nwhy\n\nRUN core/types.py changed\n",
        "FULL\nwhy\n\n",  # an older selector: no engine line
        "",  # the selector printed nothing
        "FULL\nwhy\n\nskip lowercase is not the token\n",
        "FULL\nwhy\n\nSKIPPED near miss\n",
    ],
)
def test_the_hook_runs_the_engine_suite_unless_told_skip(tmp_path: Path, canned: str):
    calls = _hook_pytest_calls(tmp_path, canned)
    assert [c for c in calls if "agents/pity_engine" in c], calls
    assert [c for c in calls if " tests " in f" {c} "], calls


# ---------------------------------------------------------------------------
# Adversary round 1 (2026-10-12): a deleted or renamed engine dependency, and
# a root pytest config file pytest would read, must RUN the engine suite.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("config", ["tox.ini", "pyproject.toml", "setup.cfg", ".pytest.ini"])
def test_a_root_pytest_config_file_runs_the_engine_suite(config):
    verdict, reason = _engine(["tools/precommit_gate.py", config])
    assert verdict == sel.ENGINE_RUN, (config, reason)


def test_a_deleted_python_file_runs_the_engine_suite():
    verdict, reason = sel.engine_decision(
        ["tools/precommit_gate.py", "core/gone.py"],
        closure=_CLOSURE, top_names=_TOP_NAMES, last_failed=(), deleted=["core/gone.py"],
    )
    assert verdict == sel.ENGINE_RUN, reason
    assert "deleted" in reason


def test_a_deleted_non_python_file_outside_the_closure_still_skips():
    """The legitimate neighbour: deleting a doc must not cost the engine run."""
    verdict, reason = sel.engine_decision(
        ["docs/old.md"],
        closure=_CLOSURE, top_names=_TOP_NAMES, last_failed=(), deleted=["docs/old.md"],
    )
    assert verdict == sel.ENGINE_SKIP, reason


def test_cli_runs_the_engine_when_its_import_is_deleted(repo_with_engine: Path):
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    _git(repo_with_engine, "rm", "-q", "core/thing.py")
    _git(repo_with_engine, "commit", "-q", "-m", "delete")
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(sel.ENGINE_RUN), lines


def test_cli_runs_the_engine_when_its_import_is_renamed(repo_with_engine: Path):
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    _git(repo_with_engine, "mv", "core/thing.py", "core/thing_renamed.py")
    _git(repo_with_engine, "commit", "-q", "-m", "rename")
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(sel.ENGINE_RUN), lines


def test_cli_runs_the_engine_when_its_import_is_deleted_uncommitted(repo_with_engine: Path):
    """The hook also grades working-tree edits: an unstaged deletion counts."""
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    (repo_with_engine / "core" / "thing.py").unlink()
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(sel.ENGINE_RUN), lines


# ---------------------------------------------------------------------------
# 0i(2c) residue (a), session 73: the hook grades the files ON DISK, and
# pytest reads its configuration and conftests from disk, so an UNTRACKED
# file must count as changed. `git diff HEAD` never lists one: an untracked
# dot-prefixed ini at the root used to give a false engine SKIP locally.
# pytest 9 also reads pytest.toml and .pytest.toml, AHEAD of pytest.ini.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("config", [".pytest.ini", ".pytest.toml", "pytest.toml", "tox.ini"])
def test_an_untracked_root_pytest_config_runs_the_engine_suite(
    repo_with_engine: Path, config: str
):
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    _commit_tools_change(repo_with_engine)
    (repo_with_engine / config).write_text("[pytest]\n", encoding="ascii", newline="\n")
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(f"{sel.ENGINE_RUN} "), lines
    assert config in lines[3], lines


def test_an_untracked_conftest_under_agents_runs_the_engine_suite(repo_with_engine: Path):
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    _commit_tools_change(repo_with_engine)
    (repo_with_engine / "agents" / "pity_engine" / "conftest.py").write_text(
        "X = 1\n", encoding="ascii", newline="\n"
    )
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(f"{sel.ENGINE_RUN} "), lines


def test_untracked_docs_and_ignored_files_still_skip_the_engine(repo_with_engine: Path):
    """The legitimate neighbours: an untracked note and a gitignored scratch
    `.py` reach nothing the engine reads, so the SKIP must survive."""
    (repo_with_engine / ".gitignore").write_text("scratch/\n", encoding="ascii", newline="\n")
    _git(repo_with_engine, "add", "-A")
    _git(repo_with_engine, "commit", "-q", "-m", "ignore")
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    _commit_tools_change(repo_with_engine)
    (repo_with_engine / "docs").mkdir()
    (repo_with_engine / "docs" / "note.md").write_text("n\n", encoding="ascii", newline="\n")
    (repo_with_engine / "scratch").mkdir()
    (repo_with_engine / "scratch" / "probe.py").write_text("P = 1\n", encoding="ascii", newline="\n")
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(f"{sel.ENGINE_SKIP} "), lines


@pytest.mark.parametrize("config", ["pytest.toml", ".pytest.toml"])
def test_a_root_pytest_toml_falls_back_to_the_whole_application_suite(config):
    """pytest 9 reads pytest.toml and .pytest.toml BEFORE pytest.ini, so either
    one reconfigures every application module, exactly like pytest.ini."""
    got = _select(["core/resin.py", config])
    assert got.mode == sel.FULL, got
    assert sel.ci_mark_for([config]) == ""


def test_an_untracked_root_pytest_toml_makes_the_cli_select_full(repo_with_engine: Path):
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    _commit_tools_change(repo_with_engine)
    (repo_with_engine / ".pytest.toml").write_text("[pytest]\n", encoding="ascii", newline="\n")
    assert _cli_lines(repo_with_engine, "--base", base)[0] == sel.FULL


# ---------------------------------------------------------------------------
# 0i(2c) residue (b), session 73: a FORCE-PUSH moves the remote from <base>
# to HEAD, so what changes on the remote is the two-dot diff <base> HEAD. The
# three-dot diff <base>...HEAD only lists HEAD's side since the merge-base and
# misses a remote-only engine change the force-push discards.
# ---------------------------------------------------------------------------


def _diverge(repo: Path, discarded: str) -> str:
    """Commit a change to `discarded` (the remote tip), rewind, commit a tools
    change instead, and return the discarded tip's sha (the hook's base)."""
    target = repo / discarded
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("DISCARDED = 1\n", encoding="ascii", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "remote-only")
    remote_tip = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "reset", "-q", "--hard", "HEAD~1")
    _commit_tools_change(repo)
    return remote_tip


def test_a_force_push_discarding_an_engine_change_runs_the_engine(repo_with_engine: Path):
    base = _diverge(repo_with_engine, "agents/pity_engine/__init__.py")
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(f"{sel.ENGINE_RUN} "), lines
    assert "agents/pity_engine/__init__.py" in lines[3], lines


def test_a_force_push_discarding_an_application_change_selects_its_module(
    repo_with_engine: Path,
):
    """The sibling on the application half: the same blind spot dropped the
    modules that mention a discarded change."""
    base = _diverge(repo_with_engine, "core/thing.py")
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[0] == sel.SELECT, lines
    assert "tests/test_thing.py" in lines[2].split(","), lines


def test_a_force_push_discarding_only_a_doc_still_skips_the_engine(repo_with_engine: Path):
    """The legitimate neighbour: a discarded doc reaches nothing the engine reads."""
    base = _diverge(repo_with_engine, "docs/old.md")
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(f"{sel.ENGINE_SKIP} "), lines


# ---------------------------------------------------------------------------
# Adversary round 1 on the session 73 slice. (1) `pytest tests` reads the
# first config it finds IN tests/ before the root pytest.ini, and `pytest
# agents/pity_engine` the first in agents/pity_engine/; a conftest.py anywhere
# can change collection. (2) A non-zero base sha absent from the local object
# store (a force-push over unfetched commits) must not fall back to @{u}.
# ---------------------------------------------------------------------------

_PYTEST_CONFIG_NAMES = [
    "pytest.toml", ".pytest.toml", "pytest.ini", ".pytest.ini",
    "pyproject.toml", "tox.ini", "setup.cfg",
]


@pytest.mark.parametrize("name", _PYTEST_CONFIG_NAMES)
def test_a_pytest_config_directly_under_tests_forces_full(name: str):
    path = f"tests/{name}"
    got = _select(["core/resin.py", path])
    assert got.mode == sel.FULL, got
    assert path in got.reason
    assert sel.ci_mark_for([path]) == ""


@pytest.mark.parametrize("name", _PYTEST_CONFIG_NAMES)
def test_an_untracked_pytest_config_under_tests_makes_the_cli_select_full(
    repo_with_engine: Path, name: str
):
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    _commit_tools_change(repo_with_engine)
    (repo_with_engine / "tests" / name).write_text("[pytest]\n", encoding="ascii", newline="\n")
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[0] == sel.FULL, lines


@pytest.mark.parametrize("name", _PYTEST_CONFIG_NAMES)
def test_an_untracked_pytest_config_in_the_engine_package_runs_the_engine(
    repo_with_engine: Path, name: str
):
    base = _git(repo_with_engine, "rev-parse", "HEAD").strip()
    _commit_tools_change(repo_with_engine)
    (repo_with_engine / "agents" / "pity_engine" / name).write_text(
        "[pytest]\n", encoding="ascii", newline="\n"
    )
    lines = _cli_lines(repo_with_engine, "--base", base)
    assert lines[3].startswith(f"{sel.ENGINE_RUN} "), lines


@pytest.mark.parametrize("path", ["tests/sub/conftest.py", "core/conftest.py", "tools/conftest.py"])
def test_a_conftest_anywhere_forces_full_and_runs_the_engine(path: str):
    got = _select(["core/resin.py", path])
    assert got.mode == sel.FULL, got
    verdict, reason = _engine([path])
    assert verdict == sel.ENGINE_RUN, reason


@pytest.mark.parametrize("path", ["tests/data/sample.ini", "docs/setup.cfg.md", "tools/tox_helper.py"])
def test_config_like_neighbours_keep_their_mapping(path: str):
    """The legitimate neighbours: only the exact config names directly under
    tests/ (or the root) are FULL triggers, never a lookalike or a deeper ini."""
    assert _select([path]).mode != sel.FULL


def test_a_base_sha_missing_locally_forces_full(repo: Path):
    """The adversary's probe: an upstream exists at HEAD~1, so the old code
    silently diffed against it and SELECTed."""
    first = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "core" / "thing.py").write_text("X = 2\n", encoding="ascii", newline="\n")
    _git(repo, "commit", "-q", "-am", "change")
    _git(repo, "remote", "add", "origin", ".")
    _git(repo, "update-ref", "refs/remotes/origin/main", first)
    _git(repo, "branch", "-M", "master")
    _git(repo, "config", "branch.master.remote", "origin")
    _git(repo, "config", "branch.master.merge", "refs/heads/main")
    assert _git(repo, "rev-parse", "@{u}").strip() == first, "non-vacuity: @{u} resolves"
    missing = "1234567890" * 4
    mode, reason, _ = _cli(repo, "--base", missing)
    assert mode == sel.FULL, (mode, reason)
    assert "missing" in reason, reason
    lines = _cli_lines(repo, "--base", missing)
    assert lines[3].startswith(sel.ENGINE_RUN), lines
    assert _cli_raw(repo, "--ci-mark", "--base", missing).strip() == ""


def test_an_all_zero_base_still_takes_the_upstream_route(repo: Path):
    """The legitimate neighbour: a new remote ref (all-zero sha) keeps @{u}."""
    first = _git(repo, "rev-parse", "HEAD").strip()
    (repo / "core" / "thing.py").write_text("X = 2\n", encoding="ascii", newline="\n")
    _git(repo, "commit", "-q", "-am", "change")
    _git(repo, "remote", "add", "origin", ".")
    _git(repo, "update-ref", "refs/remotes/origin/main", first)
    _git(repo, "branch", "-M", "master")
    _git(repo, "config", "branch.master.remote", "origin")
    _git(repo, "config", "branch.master.merge", "refs/heads/main")
    mode, reason, modules = _cli(repo, "--base", "0" * 40)
    assert mode == sel.SELECT, (mode, reason)
    assert "tests/test_thing.py" in modules.split(","), modules


# ---------------------------------------------------------------------------
# 0i residue (e), session 73: every git call is bounded by a timeout. A hung
# git child (a partial clone whose missing-sha rev-parse reaches the network,
# a lock another process holds) used to hang the pre-push hook forever. Every
# call now carries GIT_TIMEOUT_S, and a timeout is a FAILED git call: the
# selector fails closed to FULL and --ci-mark to every module.
# ---------------------------------------------------------------------------


def _recording_run(calls: list[dict], stdout: str = ""):
    def run(cmd, **kwargs):
        calls.append({"cmd": list(cmd), **kwargs})
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    return run


def _hung_run(calls: list[dict]):
    def run(cmd, **kwargs):
        calls.append({"cmd": list(cmd), **kwargs})
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout") or 0)

    return run


def test_every_runtime_git_call_carries_the_documented_timeout(monkeypatch, tmp_path: Path):
    calls: list[dict] = []
    monkeypatch.setattr(sel.subprocess, "run", _recording_run(calls, stdout="deadbeef\n"))
    assert sel._changed(tmp_path, "deadbeef") is not None
    sel._git_grep(tmp_path)(["core/thing.py"])
    assert len(calls) == 6, "non-vacuity: rev-parse, three diffs, ls-files, grep"
    for call in calls:
        assert call.get("timeout") is not None, f"no timeout on {call['cmd']}"
        assert call["timeout"] == sel.GIT_TIMEOUT_S, call
    assert 0 < sel.GIT_TIMEOUT_S <= 120


def test_every_subprocess_call_in_the_source_passes_a_timeout():
    """The sibling sweep: a future subprocess call added without one reds here."""
    import ast

    tree = ast.parse((REPO_ROOT / "scripts" / "prepush_select.py").read_bytes())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
    ]
    assert calls, "non-vacuity: the selector does shell out to git"
    for node in calls:
        assert "timeout" in {kw.arg for kw in node.keywords}, f"line {node.lineno}"


def test_a_hung_git_call_is_a_failed_git_call(monkeypatch, tmp_path: Path):
    calls: list[dict] = []
    monkeypatch.setattr(sel.subprocess, "run", _hung_run(calls))
    assert sel._git(tmp_path, "rev-parse", "HEAD") is None
    assert len(calls) == 1, "non-vacuity: the fake git was reached"


def test_a_hung_git_call_fails_closed_to_the_whole_suite(
    monkeypatch, tmp_path: Path, capsysbinary
):
    monkeypatch.setattr(sel.subprocess, "run", _hung_run([]))
    assert sel.main(["--root", str(tmp_path), "--base", "deadbeef"]) == 0
    lines = capsysbinary.readouterr().out.decode("ascii").split("\n")
    assert lines[0] == sel.FULL, lines
    assert "selector error" not in lines[1], "a timeout is a git failure, not a crash"
    assert lines[3].startswith(sel.ENGINE_RUN), lines


def test_a_hung_git_grep_fails_closed_to_the_whole_suite(
    monkeypatch, tmp_path: Path, capsysbinary
):
    """Only the grep hangs: the diff succeeds, so the FULL comes from the grep."""

    def run(cmd, **kwargs):
        if cmd[1] == "grep":
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout") or 0)
        out = "deadbeef\n" if cmd[1] == "rev-parse" else "core/thing.py\n"
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(sel.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="git grep"):
        sel._git_grep(tmp_path)(["core/thing.py"])
    assert sel.main(["--root", str(tmp_path), "--base", "deadbeef"]) == 0
    assert capsysbinary.readouterr().out.decode("ascii").split("\n")[0] == sel.FULL


def test_a_hung_git_call_under_ci_mark_runs_every_module(
    monkeypatch, tmp_path: Path, capsysbinary
):
    monkeypatch.setattr(sel.subprocess, "run", _hung_run([]))
    assert sel.main(["--root", str(tmp_path), "--base", "deadbeef", "--ci-mark"]) == 0
    assert capsysbinary.readouterr().out == b"\n"


def test_a_healthy_git_call_is_untouched_by_the_timeout(repo: Path):
    """The legitimate neighbour: a real, fast git call still answers."""
    assert sel._git(repo, "rev-parse", "HEAD") == _git(repo, "rev-parse", "HEAD")
