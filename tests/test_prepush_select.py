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


def test_render_is_three_lines_mode_reason_modules():
    out = sel.render(sel.Selection(sel.SELECT, "why", ("tests/test_a.py", "tests/test_b.py")))
    assert out.split("\n") == [sel.SELECT, "why", "tests/test_a.py,tests/test_b.py"]


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
    return out.removesuffix("\n").split("\n")


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
