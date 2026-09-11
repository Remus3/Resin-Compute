"""Repo-root pytest hooks - apply to BOTH suites.

`tests/conftest.py` only reaches `tests/`. The engine suite under
`agents/pity_engine/tests/` needs the same repo root on `sys.path` to import
`core.types`, and a rootdir conftest is the only place one installation covers
both. This mirrors Sibling-C's root conftest for the same reason.

That same reach is why `pytest_runtest_makereport` lives here rather than in
`tests/conftest.py`. Tests in both suites patch `os.name` to reach a
Windows-only branch, and pytest builds the failure report for a phase while that
patch is STILL LIVE:

    _pytest.runner.call_and_report
      -> ihook.pytest_runtest_makereport
      -> TestReport.from_item_and_call
      -> _format_failed_longrepr            (_pytest/reports.py:263)
      -> Node._repr_failure_py              (_pytest/nodes.py:444)

whose first act is `Path(os.getcwd()) != self.config.invocation_params.dir`,
guarded only by `except OSError`. `pathlib.Path` dispatches on `os.name`, so on
a POSIX host that constructs a `WindowsPath`, which raises - and the raise is
not an OSError, so pytest aborts the whole run with INTERNALERROR instead of
naming the failing test. A failure that cannot be named cannot be fixed. There
is no `WindowsPath` literal anywhere in this tree; it arrives purely through
that dispatch.

Scope, deliberately narrow:

- Only `pytest_runtest_makereport` is wrapped. It is the single hook through
  which the setup, call AND teardown phases all build their reports, so one
  wrapper covers all three.
- `pytest_runtest_setup` / `pytest_runtest_teardown` are NOT wrapped. Those hooks
  run the test's own setup and teardown code, and a fixture that patches
  `os.name` on purpose must see its patch hold there. Their reports still go
  through `pytest_runtest_makereport` and are therefore already covered.
- `pytest_exception_interact` is NOT wrapped. `call_and_report` fires it after
  `pytest_runtest_makereport` has already materialised the longrepr into plain
  strings, and the only bundled implementations are `_pytest/debugging.py`
  (active only under `--pdb`, which CI does not pass) and
  `_pytest/faulthandler.py`, which takes no arguments and cancels a timeout.
  Neither builds a `Path`.

Regression arms, including the positive control that separates a protected run
from an unprotected one, live in `tests/test_report_renderability.py`.
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent))

# Captured at import time, before any test can patch it.
_REAL_OS_NAME = os.name

# ---------------------------------------------------------------------------
# No INHERITED git environment may decide what this tree tracks.
# ---------------------------------------------------------------------------
#
# THE DEFECT, MEASURED ON git 2.53.0.windows.3 WITH EVERY RETURNCODE READ IN
# PYTHON. A throwaway repository with a main checkout, one linked worktree and a
# `pre-push` that dumps its own environment:
#
#     push from the MAIN CHECKOUT      GIT_EXEC_PATH, GIT_PREFIX
#     push from a LINKED WORKTREE      GIT_EXEC_PATH, GIT_PREFIX, and
#                                      GIT_DIR=<main>/.git/worktrees/<name>
#
# `.githooks/pre-push` runs both suites, and this tree is worked in linked
# worktrees under `.claude/worktrees/`, so a push from one of them runs every
# guard in both suites with a foreign `GIT_DIR` exported.
#
# THE CORPUS REALLY CHANGES, AND IT CHANGES AT RETURNCODE 0. Measured this tree,
# cwd at the repository root: `git ls-files` answered 224 paths clean and 1 path
# with `GIT_DIR` pointed at a throwaway repository holding a single file. There
# is no error and no non-zero exit - only a different answer. Run against the
# real suite in that state, `tests/test_readme_tree.py` reported
# `frozenset({'FOREIGN_MARKER.txt'})` as this repository's tracked listing, and
# `tests/test_shell_contract.py` ABORTED COLLECTION - exit 2, the whole module
# gone - because its `@pytest.mark.parametrize` argument came back empty.
#
# WHICH VARIABLES, DERIVED AND NOT RECALLED. Each candidate was exported in turn
# and the four git queries this tree builds corpora from - `ls-files` plain,
# `ls-files` under a pathspec, `check-attr` and `check-ignore`, plus `ls-tree` -
# were compared against the clean answer. The nine below are every candidate
# that made at least one of them answer DIFFERENTLY AND SUCCESSFULLY:
#
#   GIT_DIR                repoints the repository outright; `ls-files` and
#                          `ls-tree` then describe another tree at exit 0
#   GIT_INDEX_FILE         swaps the index `ls-files` reads, same silent effect
#   GIT_WORK_TREE          moves the tree `check-ignore` resolves rules against
#   GIT_COMMON_DIR         moves refs, so `ls-tree HEAD` resolves elsewhere
#   GIT_OBJECT_DIRECTORY   moves objects, same reach into `ls-tree`
#   GIT_LITERAL_PATHSPECS  changes every pathspec-filtered answer, and this tree
#   GIT_NOGLOB_PATHSPECS   filters by pathspec in `tests/test_commit_trailers.py`
#   GIT_GLOB_PATHSPECS     and in `tools/precommit_gate.py`
#   GIT_ICASE_PATHSPECS
#
# DELIBERATELY NOT SCRUBBED, each for a measured reason:
#
#   GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM  changed NO probe, and
#       `tests/test_hook_gate.py` sets both in its throwaway repository's child
#       environment. Removing them here buys nothing and risks that fixture.
#   GIT_CONFIG_COUNT  changes every probe by BREAKING git - exit 128, "missing
#       config key GIT_CONFIG_KEY_0". That is a loud denial, not a silent
#       substitution, and every corpus builder in this tree already fails or
#       skips on a non-zero exit. It is also the same family as the two above.
#   GIT_ALTERNATE_OBJECT_DIRECTORIES, GIT_CEILING_DIRECTORIES, GIT_NAMESPACE,
#   GIT_ATTR_NOSYSTEM, GIT_DISCOVERY_ACROSS_FILESYSTEM  changed no probe.
#   GIT_EXEC_PATH, GIT_PREFIX, GIT_EDITOR  changed no probe, and GIT_EXEC_PATH
#       is how git finds its own helpers when it is invoked from a hook.
#
# WHY HERE AND NOT IN AN AUTOUSE FIXTURE. Corpus builders in this tree run at
# IMPORT, not at test time: `tests/test_line_endings.py` calls `_measure_baseline()`
# at module scope and `tests/test_shell_contract.py` builds a parametrize argument
# from `git ls-files`. Both happen during COLLECTION, before the first fixture is
# set up, so an autouse fixture arrives too late for exactly the sites whose
# failure is worst. Module-level code in a conftest runs before any test module
# is imported, which is the only grain that covers them.
#
# WHY THE ROOT CONFTEST AND NOT `tests/conftest.py`. `tests/conftest.py` is never
# loaded for `agents/pity_engine/`, and `.githooks/pre-push` runs that suite too.
# Measured with `GIT_DIR` exported and a `-p` plugin reporting at
# `pytest_collection_finish`: before this scrub both suites saw the foreign
# `GIT_DIR`; a scrub in `tests/conftest.py` would reach only one of them. This is
# the same reasoning, and the same file, as the `RC_LOG_DIR` redirection below.
#
# WHAT IT DOES NOT REACH, STATED RATHER THAN IMPLIED. This is a mutation of THIS
# process's environment, so it covers `git` launched by the pytest process and
# by children that inherit from it. It does NOT reach `tools/precommit_gate.py`
# or `scripts/install_hooks.py` when a git hook runs them directly, AND IT MUST
# NOT: `pre-commit` exports `GIT_INDEX_FILE` on purpose, and the gate is supposed
# to grade the index that hook is committing.
#
# The arms live in `tests/test_git_env_scrub.py`, including the positive control
# that shows the corpus really does swap when the scrub is not in the way.
_GIT_ENV_SCRUBBED: tuple[str, ...] = (
    "GIT_DIR",
    "GIT_INDEX_FILE",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_LITERAL_PATHSPECS",
    "GIT_NOGLOB_PATHSPECS",
    "GIT_GLOB_PATHSPECS",
    "GIT_ICASE_PATHSPECS",
)

#: What was actually removed, kept so a reader of a failing run can see whether
#: the ambient environment was carrying anything at all. It is diagnostic and
#: nothing asserts on it - the arms feed an input and measure the corpus.
_GIT_ENV_REMOVED: dict[str, str] = {
    name: os.environ.pop(name) for name in _GIT_ENV_SCRUBBED if name in os.environ
}

# ---------------------------------------------------------------------------
# The suite must not write the operator's live day log.
# ---------------------------------------------------------------------------
#
# MEASURED, not assumed. An in-process tracer that wrapped `builtins.open`,
# `io.open`, `os.replace` and `os.rename` and charged bytes to the executing
# nodeid recorded 17492 bytes written into `logs/2026-09-11.log` by 51 named
# tests across 12 files in one `python -m pytest tests` run. A snapshot diff
# could not have established this: daemons and other sessions write these trees
# concurrently, so a file that changed during a run attributes nothing.
#
# THE MECHANISM. `core.log_setup.get_logger()` attaches a `logging.FileHandler`
# pointed at `core.config.load_config().log_dir / "<today>.log"`, and the
# degradation arms in this tree log real ERROR lines on purpose. The operator
# greps a day at a time, so their unit of review fills with synthetic failures
# that no incident produced.
#
# THE FIX IS AT THE ROOT, not at the 51 call sites. `load_config()` already
# derives `log_dir` from `RC_LOG_DIR` WHEN USED rather than caching it at
# import, so one environment redirection installed before collection isolates
# every present and future logging caller in both suites at once. A per-site
# injection would need a list kept in sync by hand, and the next test to log an
# error would rediscover the defect.
#
# It is installed HERE, at conftest import, because `_ensure_file()` caches the
# handler process-wide on first use: a redirection applied after the first
# `get_logger()` call would arrive too late. A rootdir conftest is imported
# before any test module, and is the only place one installation covers both
# `tests/` and `agents/pity_engine/`.
#
# An existing `RC_LOG_DIR` is honoured rather than overridden, so an operator
# running the suite with a deliberate redirection keeps it.
#
# The arms live in `tests/test_suite_writes_no_live_logs.py`, including the
# positive control that shows the path lands back inside the repo when this
# redirection is removed.
_LOG_REDIRECT_ENV = "RC_LOG_DIR"
_log_redirect_dir: str | None = None

if not os.environ.get(_LOG_REDIRECT_ENV, "").strip():
    _log_redirect_dir = tempfile.mkdtemp(prefix="resin-test-logs-")
    os.environ[_LOG_REDIRECT_ENV] = _log_redirect_dir


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Remove the redirected log directory this conftest created.

    Only the directory THIS process created is removed - an operator-supplied
    `RC_LOG_DIR` is left alone, and nothing under the repository is touched.
    `logging.shutdown()` closes the file handler first, because Windows refuses
    to unlink a file that is still open, and `ignore_errors` keeps a failed
    cleanup from turning a green run red.
    """
    if _log_redirect_dir is None:
        return
    logging.shutdown()
    shutil.rmtree(_log_redirect_dir, ignore_errors=True)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[Any]
) -> Generator[None, Any, Any]:
    """Hold `os.name` at the interpreter's real value while the report is built.

    The test's own value is put back afterwards so that its monkeypatch teardown,
    and any finalizer it registered, still see what they expect.
    """
    patched = os.name
    if patched != _REAL_OS_NAME:
        os.name = _REAL_OS_NAME
    try:
        return (yield)
    finally:
        if os.name != patched:
            os.name = patched
