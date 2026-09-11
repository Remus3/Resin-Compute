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
# WHERE THE POPULATION COMES FROM. It is not a list anyone recalled, and the
# first version of this block was exactly that: five names of the fifteen git
# itself calls repo-local, with seven of the remaining ten never considered at
# all. The population is `git rev-parse --local-env-vars`, GIT'S OWN ENUMERATION
# of the variables that point somewhere repo-local. On git 2.53.0.windows.3 it
# names 15. `tests/test_git_env_scrub.py` reconciles that output against the two
# tables below ON EVERY RUN, so a git that GAINS a variable reddens a test in
# this tree rather than arriving as an incident.
#
# THE CRITERION, CORRECTED - and this is the reusable part. The first pass kept
# only variables that made git answer "DIFFERENTLY AND AT RETURNCODE 0". That
# filter has a hole the defect fits through:
#
#   AN ANSWER IS THE PAIR (returncode, stdout), AND A RETURNCODE CHANGE IS AN
#   ANSWER CHANGE WHEREVER THE RETURNCODE IS THE ANSWER.
#
# `git check-ignore -q` prints nothing and says 0 for ignored, 1 for not.
# `tests/test_agent_roster.py` literally returns `completed.returncode == 0` as
# its corpus, and `tests/test_ci_workflow_complement.py` asserts on that exit
# code directly in both halves of its ignore guard. An rc-0-only filter is
# therefore STRUCTURALLY BLIND to the whole check-ignore family. Measured here:
# GIT_CONFIG_PARAMETERS flips `check-ignore -q --no-index
# core/probe_not_ignored.json` from 1 to 0, and the old filter discarded that as
# "not an rc 0 change".
#
# The criterion this file now applies, in three parts:
#
#   1. THE ANSWER CHANGED when the pair (returncode, stdout) changed.
#   2. IT IS A SILENT SUBSTITUTION when the changed answer is one a corpus
#      builder here would ACT on: a different stdout at exit 0, or a flip
#      between the documented answer codes of a returncode-as-answer command.
#      Those get scrubbed.
#   3. IT IS A LOUD DENIAL when git exits 128 with an error on stderr. Every
#      corpus builder in this tree already fails or skips on that, so a loud
#      denial is not by itself a reason to scrub. IT IS ALSO NOT A REASON TO
#      KEEP. GIT_CONFIG_COUNT denies loudly when it is malformed and substitutes
#      SILENTLY when it is well formed, and only the second disposition decides.
#      The old block kept it on the first disposition alone.
#
# THE QUERIES THE CRITERION IS APPLIED TO ARE DERIVED FROM THE TREE, not chosen
# by taste. `python -m tools.git_subprocess_census` enumerates 78 subprocess
# launch sites over its default roots, 38 of them git. 28 of those 38 resolve
# statically to a subcommand - ls-files 18, check-ignore 3, check-attr 2, and
# one each of rev-parse, diff, init, add and commit - and 10 pass a splatted
# argv no AST walk can resolve. Two consequences, both of which the first pass
# got wrong: `ls-tree` has ZERO call sites in this tree and was probed anyway,
# while `rev-parse` is the git gate itself at
# `tests/conftest.py::git_unusable_reason` and was never probed. `git log`
# reaches this tree through `tests/test_commit_trailers.py`, which enumerates
# the WHOLE HISTORY and is the corpus the graft and shallow variables truncate.
#
# SCRUBBED, each with the query it was MEASURED to substitute:
#
#   GIT_DIR                repoints the repository outright; `ls-files` went
#                          6023 bytes to 19 at exit 0
#   GIT_INDEX_FILE         swaps the index `ls-files` reads, same silent effect
#   GIT_WORK_TREE          moves the tree `check-ignore` resolves against, and
#                          `check-ignore -v --stdin` flipped rc 0 to 1
#   GIT_COMMON_DIR         moves refs; `ls-tree HEAD` resolves elsewhere
#   GIT_OBJECT_DIRECTORY   moves objects, same reach into `ls-tree`
#   GIT_CONFIG             swaps the file `git config` reads and writes:
#                          `config --list` went 1257 bytes to 148 at exit 0 and
#                          `config user.name` flipped rc 0 to 1.
#                          `tests/test_hook_gate.py` asserts
#                          `config --get core.hooksPath` is EMPTY - the exact
#                          shape a substituted config satisfies for free
#   GIT_CONFIG_PARAMETERS  GIT EXPORTS THIS ONE ITSELF. Measured in a throwaway
#                          repo whose `pre-commit` dumped its own environment,
#                          `git -c core.excludesfile=... commit` handed the hook
#                          GIT_CONFIG_PARAMETERS='core.excludesfile'='<path>' -
#                          the same delivery channel as the GIT_DIR above. With
#                          that inherited, `check-ignore -v --stdin` went 39
#                          bytes to 200 at exit 0 and `check-ignore -q` flipped
#                          rc 1 to 0
#   GIT_CONFIG_COUNT       with GIT_CONFIG_KEY_0 and GIT_CONFIG_VALUE_0 beside
#                          it, identical silent substitution to the line above.
#                          Scrubbing COUNT ALONE IS SUFFICIENT AND MINIMAL:
#                          measured, KEY_0 and VALUE_0 left exported with COUNT
#                          removed changed no probe, because git reads the count
#                          first. KEY_n and VALUE_n are not repo-local names and
#                          are not in git's list
#   GIT_GRAFT_FILE         truncates history AT EXIT 0. `git log --format=...`,
#                          which is `tests/test_commit_trailers.py`'s corpus,
#                          went 426607 bytes to 4200 and the commit count went
#                          165 to 1
#   GIT_SHALLOW_FILE       same truncation, AND `rev-parse
#                          --is-shallow-repository` flipped false to true at
#                          exit 0 - which is the gate
#                          `tests/test_commit_trailers.py::_is_shallow` reads,
#                          so the guard switches itself off
#   GIT_LITERAL_PATHSPECS  changes every pathspec-filtered answer, and this tree
#   GIT_NOGLOB_PATHSPECS   filters by pathspec in `tests/test_commit_trailers.py`
#   GIT_GLOB_PATHSPECS     and in `tools/precommit_gate.py`
#   GIT_ICASE_PATHSPECS
#
# THE FOUR PATHSPEC FLAGS ARE NOT IN GIT'S LOCAL LIST and are scrubbed anyway,
# on this tree's own measurement. The conservation arm reconciles git's list
# against what is handled; it does not forbid handling more than git names.
#
# DELIBERATELY NOT SCRUBBED. `_GIT_LOCAL_ENV_KEPT` below carries one entry per
# name, and the arm in `tests/test_git_env_scrub.py` requires every name in
# git's list to appear in exactly one of the two tables. A name git starts
# naming that is in neither reddens.
#
# GIT_CONFIG_GLOBAL AND GIT_CONFIG_SYSTEM - THE RECORD HERE WAS FALSE AND IS
# CORRECTED. The old block said they "changed NO probe". That is VALUE
# DEPENDENT and wrong: pointed at a config carrying `core.excludesFile`, EACH of
# them took `check-ignore -v --stdin` from 39 bytes to 200 at exit 0 and flipped
# `check-ignore -q` from rc 1 to rc 0 - the same power as GIT_CONFIG_PARAMETERS.
# The old block's second clause was wrong too: `tests/test_hook_gate.py` builds
# its child environment by dropping EVERY name beginning with GIT_ and then
# setting these two explicitly, so scrubbing the ambient value could not have
# risked that fixture.
#
# THE DECISION STILL STANDS, on a different and stated ground. They are not in
# `git rev-parse --local-env-vars`, and git never manufactures them - the hook
# dump above showed them only because the invoking environment already carried
# them. Their only realistic occupant here is a DELIBERATE config sandbox, which
# is what this tree's own throwaway-repo fixtures use them for; scrubbing one
# would drop that sandbox and fall back to the unsandboxed `$HOME/.gitconfig`,
# which is strictly worse. THE RESIDUAL GAP IS RECORDED RATHER THAN CLOSED: an
# ambient hostile global config still substitutes check-ignore answers here, and
# no scrub of the environment can reach `$HOME/.gitconfig` at all.
#
#   GIT_ALTERNATE_OBJECT_DIRECTORIES  changed no probe, and it can only ADD
#       object stores to the search - it cannot remove this repository's own.
#   GIT_IMPLICIT_WORK_TREE  changed no probe at "1" or at "0".
#   GIT_NO_REPLACE_OBJECTS  changed no probe, and it only DISABLES replacement.
#   GIT_REPLACE_REF_BASE  changed no probe. It names a ref namespace INSIDE this
#       repository rather than a path outside it, so an attacker would already
#       have had to write refs here.
#   GIT_PREFIX  changed no probe across all thirteen queries, including one run
#       from a subdirectory. Git exports it to every hook, and it is how a hook
#       learns where it was invoked from.
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
    "GIT_CONFIG",
    "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT",
    "GIT_GRAFT_FILE",
    "GIT_SHALLOW_FILE",
    "GIT_LITERAL_PATHSPECS",
    "GIT_NOGLOB_PATHSPECS",
    "GIT_GLOB_PATHSPECS",
    "GIT_ICASE_PATHSPECS",
)

#: Every name `git rev-parse --local-env-vars` reports that this file
#: deliberately LEAVES IN PLACE, each mapped to the measured reason.
#:
#: This table is not decoration. `tests/test_git_env_scrub.py` requires the
#: union of this mapping and `_GIT_ENV_SCRUBBED` to cover git's own list, so a
#: name that is in neither - a variable a future git gains, or one dropped from
#: the tuple by hand - reddens a test instead of silently going unhandled. That
#: is the whole reason the population is read FROM GIT at runtime rather than
#: transcribed here.
_GIT_LOCAL_ENV_KEPT: dict[str, str] = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES": (
        "changed no probe, and it can only ADD object stores to the search - it "
        "cannot remove this repository's own"
    ),
    "GIT_IMPLICIT_WORK_TREE": 'changed no probe at "1" or at "0"',
    "GIT_NO_REPLACE_OBJECTS": "changed no probe, and it only DISABLES replacement",
    "GIT_REPLACE_REF_BASE": (
        "changed no probe. It names a ref namespace INSIDE this repository rather "
        "than a path outside it"
    ),
    "GIT_PREFIX": (
        "changed no probe across thirteen queries including one run from a "
        "subdirectory. Git exports it to every hook, and it is how a hook learns "
        "where it was invoked from"
    ),
}

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
