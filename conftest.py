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
import threading
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
# by taste. `python -m tools.git_subprocess_census` enumerates 85 subprocess
# call sites over its default roots, 38 of them git. 28 of those 38 resolve
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


# ---------------------------------------------------------------------------
# No test may touch the MACHINE-WIDE slot bucket. A behavioural fence.
# ---------------------------------------------------------------------------
#
# `ops.loop.slots.DEFAULT_ROOT` is a directory under C:\ProgramData that sibling
# repositories hold lanes in LIVE. Since `headless/runner.py` wraps every live
# pass in `slots.hold()`, any test that drives a live pass without naming its
# own `slot_root` acquires there - consuming a sibling's lane, or waiting out a
# 300-second timeout when the bucket is full.
#
# WHY A HOOK AND NOT ANOTHER SHAPE GUARD. The AST guards in
# `tests/test_headless_runner.py` and `tests/test_headless_runner_slots.py` read
# call SHAPES. An adversary showed they cannot carry the claim: turning an
# in-process `main(["--once", "--dry-run"])` into `main(["--once"])` defeated
# both while the arm went to the live bucket. This hook reads the PATH ARGUMENT
# of an audit event instead, so how the Python call that produced the event was
# written does not matter. How the PATH is spelled does - see below.
#
# EXACTLY WHAT IS FENCED. An audit event that is (1) raised IN THIS INTERPRETER,
# (2) named in `_FENCED_EVENTS` below, and (3) carries a str, bytes or PathLike
# argument at a listed position which, after `os.path.normpath` and
# `os.path.normcase` - and joining onto the cwd when relative - EQUALS the
# normalised `DEFAULT_ROOT` or starts with it plus a separator.
#
# WHAT IS NOT FENCED, measured by an adversary or known by construction:
#
#   - ALIAS SPELLINGS of the bucket, each of which normalises to a different
#     string: the `\\?\C:\...` and `\\.\C:\...` device prefixes, the 8.3 short
#     name (`C:\PROGRA~3\...`), a trailing dot or trailing space on a component,
#     an administrative share such as `\\localhost\C$\...`, and any junction,
#     symlink or `subst` drive that resolves into the bucket. The matcher is
#     deliberately NOT widened to chase these: a spelling list is the shape
#     matcher again, and it cannot be finished.
#   - CHILD PROCESSES. Audit hooks are per-interpreter and nothing launched by a
#     test inherits this one. The early-warning shape guard in
#     `tests/test_headless_runner.py` parses ONLY ITS OWN FILE, so it watches
#     the literal child launches in that one file and nothing else. A child
#     process launched from ANY OTHER test file is watched by no guard in THIS
#     process; the one exception is a child pytest that loads a copy of this
#     conftest, which installs its own fence inside that child.
#     Extending the fence via a
#     PYTHONPATH `sitecustomize` would alter the environment the
#     interpreter-pinning and env-scrub arms measure, so it was not done.
#   - NATIVE CODE that emits no path event: `sqlite3` opening a database file,
#     `ctypes` calling `CreateFileW` or any other Win32 file API, and any C
#     extension doing its own IO.
#   - EVENTS NOT IN THE TABLE, e.g. `os.chown`, `os.chflags`, the xattr family,
#     `os.startfile`; and READS that raise no event at all, such as `os.stat`
#     and `Path.exists`.
#   - `dir_fd`-RELATIVE CALLS: a relative path resolved against a directory
#     descriptor is joined here onto the cwd instead, so one aimed into the
#     bucket is misjudged.
#   - PYTEST-XDIST RUNS, for the session-finish backstop described below. Under
#     `-n`, each worker's `pytest_sessionfinish` result never reaches the
#     controller's exit status: measured by an adversary with pytest-xdist
#     3.8.0, installed on this host, at `-n 2`, a
#     hit during collection and a leftover-thread hit in a worker both exited
#     0. Per-test attribution still fails the test that a hit lands in. No
#     xdist plumbing is built: `pytest.ini`, `.github/workflows/ci.yml`,
#     `.github/workflows/docs-guards.yml`, `.githooks/` and `scripts/` never
#     pass `-n`.
#
# HOW A HIT FAILS, AND WHY IT IS LOUD IN ANY THREAD. Audit events are raised
# BEFORE the operation, so a fenced event raises and the operation does not
# happen. The error derives from BaseException on purpose: `slots.try_acquire`
# swallows OSError in a loop and the job runner absorbs Exception. But an
# exception inside a `threading.Thread` does not fail the test that started it
# - pytest only warns - so every hit is ALSO appended to `_SLOT_FENCE_HITS`. The
# autouse fixture `_slot_fence_attribution` fails the test during whose run a
# hit was recorded unless that test acknowledged it through the
# `slot_fence_ledger` fixture - `acknowledge(expected)` may be called ONLY from
# the main thread, and it fails unless exactly `expected` hits carrying the main
# thread's ident landed during this test. It COUNTS hits; it does not identify
# which ones. Main-thread-only is what makes the count trustworthy: a worker's
# ident can be reused by a later thread, the main thread's cannot while the
# session runs - and `pytest_sessionfinish` fails
# the run (outside xdist, see above) for any
# hit never attributed to a test (one recorded during collection, say). A hit
# from a thread that OUTLIVES its test is charged to whichever test is running
# when it lands, and one landing after the last teardown is reported at
# session finish; one landing after session finish is not reported.
#
# COST. `sys.addaudithook` cannot be removed, and it sees EVERY audit event in
# the process. The first statement is a dict lookup that drops every event not
# in the table, so the steady-state cost is one hash per event.
#
# THE ROOT IS READ FROM THE MODULE, never spelled here. A plain import of
# `ops.loop.slots` has no side effect and changes nothing in it. A relative
# DEFAULT_ROOT - which is what the Windows literal becomes on POSIX - is resolved
# against the cwd AT EVENT TIME, because that is how `hold()` will resolve it.
#
# The arms live in `tests/test_headless_runner_slots.py`, sections 7 and 8.
#
# WHEN `ops` IS NOT IMPORTABLE THE FENCE IS NOT INSTALLED. That happens only when
# this file is copied OUT of the tree - `tests/test_report_renderability.py`
# does exactly that, into a bare temp directory - and there no code that could
# reach the bucket is importable either. Inside the tree a silent disable cannot
# pass unnoticed: section 7's arms raise a SYNTHETIC event and go red, and the
# live arm there refuses to drive a pass at all, when no hook refuses it.
try:
    from ops.loop import slots as _slots  # noqa: E402 - after the sys.path insert
except ImportError:
    _slots = None  # type: ignore[assignment]


class SlotBucketFenceError(BaseException):
    """A test reached the machine-wide slot bucket. Never caught by Exception."""


_SLOT_BUCKET_RAW = os.fspath(_slots.DEFAULT_ROOT) if _slots is not None else ""
_SLOT_BUCKET_IS_ABS = bool(_SLOT_BUCKET_RAW) and os.path.isabs(_SLOT_BUCKET_RAW)


def _bucket_norm() -> str:
    raw = _SLOT_BUCKET_RAW if _SLOT_BUCKET_IS_ABS else os.path.join(os.getcwd(), _SLOT_BUCKET_RAW)
    return os.path.normcase(os.path.normpath(raw))


_SLOT_BUCKET_ABS_NORM = _bucket_norm() if _SLOT_BUCKET_IS_ABS else ""

# RESOLVE A PATH THE WAY THE KERNEL WILL - shared by both fences in this file.
# A relative path in an audit event is relative to the event's DIR_FD when one
# is given, and to the cwd only when it is not. Measured on CI run 37131711357
# (ubuntu, 3.11.16): POSIX `shutil.rmtree` removes each entry by NAME against an
# open directory fd - `os.rmdir(entry.name, dir_fd=topfd)` raises the audit
# event ('os.rmdir', ('moon_sync_inbox', 13)) - and pytest's own tmp_path
# teardown ran that over a tmp tree. Joining the bare name onto the cwd (the
# repo root) named the LIVE inbox, the fence raised a BaseException inside
# pytest's teardown, whose finalizer loop catches Exception only, and 141 arms
# went red behind it. Windows never raises such an event: `dir_fd=` fails with
# NotImplementedError there BEFORE any audit event, which is why the host was
# green. Each table below therefore pairs a path position with the position of
# the dir_fd that governs it, or None where the event carries none. Measured
# layouts (a recording audit hook over real calls, 3.14.4): os.remove/os.rmdir
# (path, dir_fd); os.mkdir/os.chmod (path, mode, dir_fd); os.utime (path,
# times, ns, dir_fd); os.rename/os.link (src, dst, src_dir_fd, dst_dir_fd);
# os.symlink (src, dst, dir_fd) where dir_fd governs dst only; shutil.rmtree
# (path, dir_fd) with None for absent; "open" carries NO dir_fd at all, so an
# os.open(name, dir_fd=fd) WRITE is still read against the cwd - a stated
# residual. A negative dir_fd (-1, or AT_FDCWD) means the cwd.
# UNRESOLVABLE IS NOT LIVE: when a dir_fd cannot be named (`_dir_fd_path` is
# None - any host without /proc), the path is not called fenced. Guessing the
# cwd instead is exactly the defect above. The live runtime and the live bucket
# are on the Windows host, where no dir_fd event can be raised at all.


def _dir_fd_path(fd: int) -> str | None:
    """The directory an open fd names, or None when this host cannot say."""
    try:
        return os.readlink(f"/proc/self/fd/{fd}")
    except (OSError, ValueError, NotImplementedError):
        return None


def _resolve_event_path(path: Any, dir_fd: Any) -> str | None:
    """`path` as the kernel resolves it, normcased; None if unreadable or unresolvable."""
    if isinstance(path, int):
        return None
    try:
        text = os.fsdecode(os.fspath(path))
        if not os.path.isabs(text):
            if isinstance(dir_fd, int) and not isinstance(dir_fd, bool) and dir_fd >= 0:
                base = _dir_fd_path(dir_fd)
                if base is None:
                    return None
            else:
                base = os.getcwd()
            text = os.path.join(base, text)
    except Exception:  # noqa: BLE001 - see `_under_slot_bucket`
        return None
    return os.path.normcase(os.path.normpath(text))


def _event_paths(
    spec: tuple[tuple[int, int | None], ...], args: tuple[Any, ...]
) -> list[tuple[Any, Any]]:
    """(path argument, its governing dir_fd or None) for each position in `spec`."""
    found: list[tuple[Any, Any]] = []
    for index, fd_index in spec:
        if index >= len(args):
            continue
        dir_fd = args[fd_index] if fd_index is not None and fd_index < len(args) else None
        found.append((args[index], dir_fd))
    return found


#: Fenced audit events: each maps to (path position, governing dir_fd position).
_FENCED_EVENTS: dict[str, tuple[tuple[int, int | None], ...]] = {
    "open": ((0, None),),
    "os.mkdir": ((0, 2),),
    "os.remove": ((0, 1),),
    "os.rmdir": ((0, 1),),
    "os.rename": ((0, 2), (1, 3)),
    "os.link": ((0, 2), (1, 3)),
    "os.symlink": ((0, None), (1, 2)),
    "os.listdir": ((0, None),),
    "os.scandir": ((0, None),),
    "os.chmod": ((0, 2),),
    "os.utime": ((0, 3),),
    "os.truncate": ((0, None),),
    "glob.glob": ((0, None),),
    "shutil.rmtree": ((0, 1),),
    "shutil.copyfile": ((0, None), (1, None)),
    "shutil.move": ((0, None), (1, None)),
}


def _under_slot_bucket(path: Any, dir_fd: Any = -1) -> bool:
    """True when `path` is the bucket or lies under it. A pure path predicate."""
    # A path that cannot be read is not the bucket, and the fence must never
    # break an unrelated test - several patch `os` internals on purpose.
    text = _resolve_event_path(path, dir_fd)
    if text is None:
        return False
    try:
        bucket = _SLOT_BUCKET_ABS_NORM or _bucket_norm()
    except Exception:  # noqa: BLE001 - same reason
        return False
    return text == bucket or text.startswith(bucket + os.sep)


def _slot_bucket_fence(event: str, args: tuple[Any, ...]) -> None:
    spec = _FENCED_EVENTS.get(event)
    if spec is None:
        return
    for raw, dir_fd in _event_paths(spec, args):
        if _under_slot_bucket(raw, dir_fd):
            message = (
                f"{event} on {raw!r} is inside the MACHINE-WIDE slot bucket "
                f"{_SLOT_BUCKET_RAW}, which sibling repositories hold live. Pass a "
                "slot_root under tmp_path."
            )
            # Recorded BEFORE raising: in a thread the raise reaches no test.
            # `list.append` is atomic under the GIL, so no lock is needed.
            _SLOT_FENCE_HITS.append(
                {
                    "message": message,
                    "thread": threading.current_thread().name,
                    "thread_ident": threading.get_ident(),
                    "attributed_to": None,
                    "acknowledged": False,
                }
            )
            raise SlotBucketFenceError(message)


#: Every fence hit this session, in order. Each record is attributed to the test
#: during whose run it landed, or stays unattributed and fails the session.
_SLOT_FENCE_HITS: list[dict[str, Any]] = []

if _SLOT_BUCKET_RAW:
    sys.addaudithook(_slot_bucket_fence)


class SlotFenceLedger:
    """The hits recorded since the current test started.

    A test that trips the fence ON PURPOSE calls `acknowledge(expected)` FROM
    THE MAIN THREAD with the number of hits it caused there. Only hits recorded
    with the main thread's ident are acknowledged, and the call fails the test
    unless exactly `expected` of them landed during this test.

    WHY ONLY THE MAIN THREAD. A thread ident is reused once its thread exits, so
    a worker that acknowledged by ident could clear a DEAD thread's hit that
    carried the same number. The main thread outlives every other thread, so its
    ident cannot be reused while the session runs. The check counts hits; it
    does not identify WHICH hits, so it is only as precise as that ident is
    unique. A call from any other thread is refused and the refusal is recorded,
    so it fails the test at teardown even though a raise inside a worker thread
    would only warn.
    """

    def __init__(self, start: int) -> None:
        self._start = start
        self.refusals: list[str] = []

    def hits(self) -> list[dict[str, Any]]:
        return _SLOT_FENCE_HITS[self._start:]

    def acknowledge(self, expected: int) -> int:
        if threading.current_thread() is not threading.main_thread():
            reason = (
                "acknowledge() was called from thread "
                f"{threading.current_thread().name!r}; only the main thread may "
                "acknowledge fence hits"
            )
            self.refusals.append(reason)
            pytest.fail(reason, pytrace=False)
        me = threading.get_ident()
        mine = [hit for hit in self.hits() if hit["thread_ident"] == me]
        if len(mine) != expected:
            pytest.fail(
                f"acknowledge expected {expected} fence hit(s) from this thread "
                f"during this test, but {len(mine)} landed",
                pytrace=False,
            )
        for hit in mine:
            hit["acknowledged"] = True
        return len(mine)


@pytest.fixture(autouse=True)
def _slot_fence_attribution(request: pytest.FixtureRequest) -> Generator[SlotFenceLedger, None, None]:
    """Fail the current test if a fence hit landed during it, in ANY thread."""
    ledger = SlotFenceLedger(len(_SLOT_FENCE_HITS))
    yield ledger
    landed = ledger.hits()
    for hit in landed:
        hit["attributed_to"] = request.node.nodeid
    if ledger.refusals:
        pytest.fail("\n".join(ledger.refusals), pytrace=False)
    loud = [hit for hit in landed if not hit["acknowledged"]]
    if loud:
        detail = "\n".join(f"  [{hit['thread']}] {hit['message']}" for hit in loud)
        pytest.fail(
            f"{len(loud)} slot-bucket fence hit(s) landed during this test and were "
            f"not acknowledged:\n{detail}",
            pytrace=False,
        )


@pytest.fixture()
def slot_fence_ledger(_slot_fence_attribution: SlotFenceLedger) -> SlotFenceLedger:
    """The current test's ledger, for arms that trip the fence on purpose."""
    return _slot_fence_attribution


def _report_unattributed_fence_hits(session: pytest.Session) -> None:
    """Fail the run for any fence hit that no test was charged with."""
    stray = [hit for hit in _SLOT_FENCE_HITS if hit["attributed_to"] is None]
    if not stray:
        return
    lines = [
        f"{len(stray)} slot-bucket fence hit(s) were never attributed to a test "
        "(collection, or a thread outliving its test):"
    ]
    lines += [f"  [{hit['thread']}] {hit['message']}" for hit in stray]
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    for line in lines:
        if reporter is not None:
            reporter.write_line(line, red=True)
        else:
            print(line, file=sys.stderr)
    session.exitstatus = pytest.ExitCode.TESTS_FAILED


# ---------------------------------------------------------------------------
# LIVE RESPONDER RUNTIME GUARD.
#
# MEASURED 2026-10-03 in the MAIN checkout: a suite run wrote the LIVE runtime.
# `ops/runtime/responder_runs.json` gained six rows the scheduled responder never
# reserved - and every one of them counts against the real daily run cap - the
# lock file beside it was created, and `responder_invocations.log` gained 103
# `fail-closed:run-lock-busy` lines. Two routes, both re-measured in a worktree:
#
#   IN PROCESS - a fixture that loads the responder without redirecting its
#   `DEFAULT_*` records and then drives `_spawn_headless`, which reserves a run
#   against the module-level `DEFAULT_RUNS`.
#   CHILD PROCESS - an interpreter launched with `sys.executable` loads the
#   module afresh, so no fixture's redirect reaches it, and with
#   `RESINCOMPUTE_RUNTIME_DIR` unset it resolves `<repo root>/ops/runtime`.
#
# Hence two halves, chosen for what each route allows:
#
# 1. THE FENCE (in process; PREVENTS). An audit hook refuses every WRITE event on
#    a responder record in the live runtime before it happens, exactly as the
#    slot fence above refuses the machine-wide bucket, and with the same
#    per-test attribution and the same BaseException so no `except Exception`
#    in the responder can swallow it. Reads pass. It needs NO timing tolerance:
#    an audit hook sees only this interpreter, so the live scheduled task -
#    another process, writing the same files every five minutes - can never
#    trip it. That is why it is the primary half and not the stat check.
# 2. THE DRIFT CHECK (any process; DETECTS). A child is beyond any hook of ours,
#    so each test snapshots the size and mtime of every live responder record
#    and fails if one changed during it. The live task DOES write these, so a
#    change is excused only when the test overlapped a SCHEDULED FIRE, read back
#    from the invocation log itself: a `scheduledtask` `start` line opens a fire
#    and that source's next line closes it, an unclosed start for at most five
#    minutes. No other source opens one - a leaking child writes its own `cli`
#    lines, and those must not excuse it. The blind spots are stated, not
#    hidden: a child that leaks DURING a scheduled fire is excused, and so is
#    one that forges the `scheduledtask` label. The armed task's working
#    directory is the MAIN checkout, so in a worktree the log normally holds no
#    such line and nothing is excused - but that is a property of how the task
#    is armed today, not of the check, and the check does not rely on it.
#
# SCOPE IS TREE-WIDE, deliberately. The measured row-writer was not in the file
# first suspected, which is the argument against fencing a named file list.
#
# THE LIVE DIRECTORY is resolved once, from `ops.health.runtime_dir()` as this
# session starts - the env override if the operator exported one, else
# `<repo root>/ops/runtime` - and the repo default is fenced as well. A test that
# monkeypatches the variable to `tmp_path` therefore points AWAY from the fence.
try:
    from ops.health import runtime_dir as _runtime_dir  # noqa: E402
except ImportError:
    _runtime_dir = None  # type: ignore[assignment]


class LiveRuntimeFenceError(BaseException):
    """A test tried to write a live responder record. Never caught by Exception."""


def _norm(path: Any) -> str:
    text = os.fsdecode(os.fspath(path))
    if not os.path.isabs(text):
        text = os.path.join(os.getcwd(), text)
    return os.path.normcase(os.path.normpath(text))


def _live_runtime_dirs() -> tuple[str, ...]:
    if _runtime_dir is None:
        return ()
    found = {_norm(_runtime_dir()), _norm(Path(__file__).parent / "ops" / "runtime")}
    return tuple(sorted(found))


_LIVE_RUNTIME_DIRS = _live_runtime_dirs()

#: A responder record's name, after an atomic temp file's leading dot is
#: stripped. `trial_confirmed.json` is the agreement record, also a responder
#: `DEFAULT_` under the runtime; the arm in `tests/test_responder_uniform_budget.py`
#: derives the full `DEFAULT_` set from the module and fails if one escapes this.
_RESPONDER_RECORD_PREFIXES = ("responder", "trial_confirmed")


def _live_extra_paths() -> tuple[str, ...]:
    """The responder's `DEFAULT_` paths OUTSIDE the runtime dir, fenced whole.

    This repo's own inbox, the roots map and the machine-level trust config.
    Sibling inboxes - where a delivery lands - are external and not fenced.
    """
    if _runtime_dir is None:
        return ()
    root = Path(__file__).parent
    found = {_norm(root / "moon_sync_inbox"), _norm(root / "ops" / "moon_sync_repos.json")}
    try:
        found.add(_norm(Path.home() / ".claude.json"))
    except (OSError, RuntimeError):
        pass
    return tuple(sorted(found))


_LIVE_EXTRA_PATHS = _live_extra_paths()


def _is_live_responder_record(path: Any, dir_fd: Any = -1) -> bool:
    """True for a responder record, its lock or temp sibling, the staging tree,
    or one of the out-of-runtime `DEFAULT_` paths in `_LIVE_EXTRA_PATHS`.

    A relative `path` is resolved against `dir_fd` when one is given, exactly as
    the slot fence does - see `_resolve_event_path` for the CI run that made
    joining it onto the cwd a defect."""
    # An unreadable path, or one whose dir_fd cannot be named, is not a record.
    text = _resolve_event_path(path, dir_fd)
    if text is None:
        return False
    for extra in _LIVE_EXTRA_PATHS:
        if text == extra or text.startswith(extra + os.sep):
            return True
    for live in _LIVE_RUNTIME_DIRS:
        if not text.startswith(live + os.sep):
            continue
        first = text[len(live) + 1:].split(os.sep, 1)[0]
        if first.lstrip(".").startswith(_RESPONDER_RECORD_PREFIXES):
            return True
    return False


_WRITE_OPEN_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

#: Write-side audit events: (path position, governing dir_fd position), as in
#: `_FENCED_EVENTS` above.
_RUNTIME_WRITE_EVENTS: dict[str, tuple[tuple[int, int | None], ...]] = {
    "os.rename": ((0, 2), (1, 3)),
    "os.remove": ((0, 1),),
    "os.rmdir": ((0, 1),),
    "os.mkdir": ((0, 2),),
    "os.link": ((0, 2), (1, 3)),
    "os.symlink": ((0, None), (1, 2)),
    "os.chmod": ((0, 2),),
    "os.utime": ((0, 3),),
    "os.truncate": ((0, None),),
    "shutil.rmtree": ((0, 1),),
    "shutil.copyfile": ((1, None),),
    "shutil.move": ((0, None), (1, None)),
}

_RUNTIME_FENCE_HITS: list[dict[str, Any]] = []


def _is_write_open(args: tuple[Any, ...]) -> bool:
    mode = args[1] if len(args) > 1 else None
    flags = args[2] if len(args) > 2 else None
    if isinstance(flags, int) and flags & _WRITE_OPEN_FLAGS:
        return True
    return isinstance(mode, str) and any(c in mode for c in "wax+")


def _live_runtime_fence(event: str, args: tuple[Any, ...]) -> None:
    if event == "open":
        if not args or not _is_write_open(args):
            return
        spec: tuple[tuple[int, int | None], ...] = ((0, None),)
    else:
        found = _RUNTIME_WRITE_EVENTS.get(event)
        if found is None:
            return
        spec = found
    for raw, dir_fd in _event_paths(spec, args):
        if _is_live_responder_record(raw, dir_fd):
            message = (
                f"{event} on {raw!r} writes a LIVE responder record. Redirect "
                "every DEFAULT_ path of the responder under tmp_path, and give any "
                "child interpreter RESINCOMPUTE_RUNTIME_DIR explicitly."
            )
            _RUNTIME_FENCE_HITS.append(
                {
                    "message": message,
                    "thread": threading.current_thread().name,
                    "thread_ident": threading.get_ident(),
                    "attributed_to": None,
                    "acknowledged": False,
                }
            )
            raise LiveRuntimeFenceError(message)


if _LIVE_RUNTIME_DIRS:
    sys.addaudithook(_live_runtime_fence)


class RuntimeFenceLedger:
    """The runtime-fence hits since the current test began; see SlotFenceLedger."""

    def __init__(self, start: int) -> None:
        self._start = start

    def hits(self) -> list[dict[str, Any]]:
        return _RUNTIME_FENCE_HITS[self._start:]

    def acknowledge(self, expected: int) -> int:
        if threading.current_thread() is not threading.main_thread():
            pytest.fail("only the main thread may acknowledge runtime-fence hits", pytrace=False)
        me = threading.get_ident()
        mine = [hit for hit in self.hits() if hit["thread_ident"] == me]
        if len(mine) != expected:
            pytest.fail(
                f"acknowledge expected {expected} runtime-fence hit(s) from this thread "
                f"during this test, but {len(mine)} landed",
                pytrace=False,
            )
        for hit in mine:
            hit["acknowledged"] = True
        return len(mine)


#: Seconds of slack around a live fire: log stamps are truncated to the second.
_FIRE_GRACE_SECONDS = 2.0
#: A `start` with no closing line - a fire still running, or one that crashed -
#: is held open at most this long, so a crashed fire cannot excuse for long.
#: Five minutes is the task's own cadence: the next fire opens its own window.
_FIRE_OPEN_CAP_SECONDS = 300.0
_FIRE_STAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
#: The ONLY source that may open an excuse window: the armed scheduled task's
#: label, `SOURCE_SCHEDULED_TASK` in `tools/moon_sync_responder.py`. REFUTED
#: 2026-10-03: when every source but `failclosed` could open one, a leaking
#: child that ran a full cycle wrote its OWN `cli start` and closing line into
#: the live log and excused its own writes. A test child can still FORGE this
#: label by setting the source variable; that residual is stated, not hidden.
_LIVE_FIRE_SOURCES = ("scheduledtask",)


def _live_fire_windows(log_text: str, now: float) -> list[tuple[float, float]]:
    """Each scheduled fire's [start, end] in epoch seconds, from the invocation log."""
    import time as _time

    windows: list[tuple[float, float]] = []
    open_at: dict[str, float] = {}
    for line in log_text.splitlines():
        parts = line.split("\t")
        if len(parts) != 4 or parts[1] not in _LIVE_FIRE_SOURCES:
            continue
        try:
            stamp = _time.mktime(_time.strptime(parts[0], _FIRE_STAMP_FORMAT))
        except (ValueError, OverflowError):
            continue
        source, outcome = parts[1], parts[3]
        if source in open_at:
            windows.append((open_at.pop(source), stamp))
        if outcome == "start":
            open_at[source] = stamp
    for start in open_at.values():
        windows.append((start, min(now, start + _FIRE_OPEN_CAP_SECONDS)))
    return sorted(windows)


def _runtime_drift(
    before: dict[str, tuple[int, int]],
    after: dict[str, tuple[int, int]],
    t0: float,
    t1: float,
    log_text: str,
    now: float,
) -> str | None:
    """A finding when a live record changed during [t0, t1] outside every live fire."""
    changed = sorted(n for n in set(before) | set(after) if before.get(n) != after.get(n))
    if not changed:
        return None
    pad = _FIRE_GRACE_SECONDS + 1.0
    for start, end in _live_fire_windows(log_text, now):
        if start - pad <= t1 and t0 <= end + pad:
            return None
    detail = ", ".join(f"{n}: {before.get(n)} -> {after.get(n)}" for n in changed)
    return (
        "a LIVE responder record changed during this test and no live fire was "
        f"running to explain it - (size, mtime_ns) {detail}. A child interpreter "
        "needs RESINCOMPUTE_RUNTIME_DIR set explicitly."
    )


def _live_runtime_snapshot() -> dict[str, tuple[int, int]]:
    """(size, mtime_ns) of every responder record directly in each live dir."""
    snap: dict[str, tuple[int, int]] = {}
    for live in _LIVE_RUNTIME_DIRS:
        try:
            entries = list(os.scandir(live))
        except OSError:
            continue
        for entry in entries:
            if not entry.name.lstrip(".").startswith(_RESPONDER_RECORD_PREFIXES):
                continue
            try:
                st = entry.stat()
            except OSError:
                continue
            snap[os.path.join(live, entry.name)] = (st.st_size, st.st_mtime_ns)
    return snap


def _live_invocation_log_text() -> str:
    for live in _LIVE_RUNTIME_DIRS:
        try:
            return Path(live, "responder_invocations.log").read_text(
                encoding="ascii", errors="replace"
            )
        except OSError:
            continue
    return ""


@pytest.fixture(autouse=True)
def _live_runtime_guard(request: pytest.FixtureRequest) -> Generator[RuntimeFenceLedger, None, None]:
    """Fail the test that wrote, or whose child wrote, a live responder record."""
    import time as _time

    ledger = RuntimeFenceLedger(len(_RUNTIME_FENCE_HITS))
    before = _live_runtime_snapshot()
    t0 = _time.time()
    yield ledger
    t1 = _time.time()
    landed = ledger.hits()
    for hit in landed:
        hit["attributed_to"] = request.node.nodeid
    loud = [hit for hit in landed if not hit["acknowledged"]]
    if loud:
        detail = "\n".join(f"  [{hit['thread']}] {hit['message']}" for hit in loud)
        pytest.fail(
            f"{len(loud)} live-runtime fence hit(s) landed during this test:\n{detail}",
            pytrace=False,
        )
    after = _live_runtime_snapshot()
    if after != before:
        finding = _runtime_drift(before, after, t0, t1, _live_invocation_log_text(), _time.time())
        if finding is not None:
            pytest.fail(finding, pytrace=False)


@pytest.fixture()
def runtime_fence_ledger(_live_runtime_guard: RuntimeFenceLedger) -> RuntimeFenceLedger:
    """The current test's runtime-fence ledger, for arms that trip it on purpose."""
    return _live_runtime_guard


def _report_unattributed_runtime_hits(session: pytest.Session) -> None:
    stray = [hit for hit in _RUNTIME_FENCE_HITS if hit["attributed_to"] is None]
    if not stray:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    for line in [f"{len(stray)} live-runtime fence hit(s) never attributed to a test:"] + [
        f"  [{hit['thread']}] {hit['message']}" for hit in stray
    ]:
        if reporter is not None:
            reporter.write_line(line, red=True)
        else:
            print(line, file=sys.stderr)
    session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Remove the redirected log directory this conftest created.

    Only the directory THIS process created is removed - an operator-supplied
    `RC_LOG_DIR` is left alone, and nothing under the repository is touched.
    `logging.shutdown()` closes the file handler first, because Windows refuses
    to unlink a file that is still open, and `ignore_errors` keeps a failed
    cleanup from turning a green run red.

    It first fails the run for any slot-bucket fence hit, or live-runtime fence
    hit, never attributed to a test - see the two fence blocks above.
    """
    _report_unattributed_fence_hits(session)
    _report_unattributed_runtime_hits(session)
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
