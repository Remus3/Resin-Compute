"""An INHERITED git environment must not decide what this tree tracks.

WHAT IS GUARDED, AND WHY IT IS NOT A SHAPE.

`conftest.py` at the repository root removes a table of git environment
variables at IMPORT. Every row arm below FEEDS ONE OF THEM AS A REAL INPUT to a
child process and then measures the answer a corpus builder would get. No row
asserts that a fixture exists, that a tuple has a given length, or that a name
appears in a file. A shape arm pins format and not input, and this tree has
shipped four of those in one day that stayed green against a mutant which broke
the property.

THE ONE THING HERE THAT IS NOT AN INPUT MEASUREMENT is the conservation check
against `git rev-parse --local-env-vars`, and it is deliberate. The row table can
only measure names somebody thought of, and the first version of this file
measured five of the fifteen names GIT ITSELF calls repo-local while seven of the
rest had never been considered anywhere. That failure is invisible to any number
of green rows, so the population is read FROM GIT at runtime and reconciled
against the conftest's two tables. It carries its own non-vacuity arm, which
feeds it a git list with an invented name in it and a scrub tuple with a real
name taken out.

THE CRITERION THE ROWS APPLY, because the next person widening this set will
need it and the first pass got it wrong. AN ANSWER IS THE PAIR (returncode,
stdout), AND A RETURNCODE CHANGE IS AN ANSWER CHANGE WHEREVER THE RETURNCODE IS
THE ANSWER. `git check-ignore -q` prints nothing and reports through its exit
code alone; `tests/test_agent_roster.py` returns `completed.returncode == 0` as
its corpus. The original scrub set was chosen by keeping only variables that
changed an answer AT EXIT 0, which is structurally blind to that whole family,
and GIT_CONFIG_PARAMETERS - which git exports to hooks itself - was discarded by
exactly that filter. Three rows in the table below change nothing but an exit
code. The full statement lives beside the tuple in `conftest.py`.

THE DEFECT, MEASURED ON git 2.53.0.windows.3. A `pre-push` hook run from a
LINKED WORKTREE inherits `GIT_DIR=<main>/.git/worktrees/<name>`; the same hook
run from the MAIN CHECKOUT inherits no `GIT_DIR` at all. `.githooks/pre-push`
runs both suites, and this tree is worked in linked worktrees, so the hook's own
configuration decides which tree the guards grade. With a foreign `GIT_DIR`
exported, `tests/test_readme_tree.py` reported this repository's tracked listing
as a one-element frozenset and `tests/test_shell_contract.py` aborted COLLECTION
at exit 2. Every one of those failures happened at git RETURNCODE 0: there is no
error to notice, only a different answer.

THE THREE POPULATIONS THIS FILE KEEPS APART.

  THE CLEAN CORPUS is what `git ls-files` says about this repository with every
  scrubbed variable absent.
  `test_the_clean_corpus_clears_its_floor_and_its_anchors` is the floor: empty it
  and that arm reddens before any comparison below can be satisfied vacuously.
  `test_gits_own_local_env_var_list_is_a_real_population` is the matching floor
  under the conservation check, for the same reason.

  THE FOREIGN CORPUS is a throwaway repository holding one file. It exists so
  that "the answer changed" is a difference a reader can see rather than an
  inequality between two opaque blobs.

  THE PER-VARIABLE ANSWERS are eight different git queries, because the scrubbed
  variables do not all reach the same one. `GIT_DIR` swaps `ls-files`;
  `GIT_WORK_TREE` leaves `ls-files` alone and moves `check-ignore`;
  `GIT_OBJECT_DIRECTORY` reaches only `ls-tree`; `GIT_GRAFT_FILE` reaches only
  `git log`. A table that probed `ls-files` for every name would have most of its
  rows measuring nothing and would still be green, so each row carries the query
  its variable was MEASURED to change, and each row asserts that change before
  asserting the scrub removes it.

  WHICH QUERIES THOSE ARE IS DERIVED FROM THE TREE rather than chosen. Run
  `python -m tools.git_subprocess_census`: 78 subprocess launch sites over its
  default roots, 38 of them git, 28 of those resolving statically to a
  subcommand - ls-files 18, check-ignore 3, check-attr 2, one each of rev-parse,
  diff, init, add and commit - with 10 splatted argvs no AST walk can resolve.
  `ls-tree` has ZERO call sites here and the first version of this table probed
  it for two rows anyway.

WHY THE CHILD PROCESS. The scrub runs when the root conftest is IMPORTED, so by
the time any test body executes it has already happened. Setting a variable
in-process afterwards would test nothing: the question is what happens to a
variable that is ALREADY EXPORTED when the conftest is imported, and only a
fresh process can be in that state.

WHY BOTH SUITES ARE PROBED FOR REAL. `tests/conftest.py` is never loaded for
`agents/pity_engine/`, and `.githooks/pre-push` runs that suite too. Moving the
scrub there would leave the engine suite unprotected while every other arm in
this file stayed green, so
`test_the_scrub_reaches_both_suites_under_a_real_pytest_run` runs an actual
pytest over each suite with `GIT_DIR` exported and reads the environment back
out through a plugin. Its control runs the same plugin over a directory OUTSIDE
this repository, where neither conftest is loaded, and REQUIRES `GIT_DIR` to
survive - otherwise a reporting mechanism that always said None would satisfy
both halves.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest

import conftest as root_conftest
from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Every variable the root conftest removes. This list is NOT the assertion -
#: it is the list of inputs the table below feeds. Deleting a row deletes a
#: measurement rather than weakening a check, which is why each row also carries
#: its own positive control.
_SCRUBBED = (
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

#: Names that ride along with a scrubbed one in a row's exported environment but
#: are NOT themselves scrubbed. `GIT_CONFIG_KEY_0` and `GIT_CONFIG_VALUE_0` are
#: meaningless to git without `GIT_CONFIG_COUNT`, which is why removing the
#: count alone is sufficient - the `GIT_CONFIG_COUNT` row below MEASURES that by
#: leaving these two exported across its scrubbed half.
_COMPANIONS = ("GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0")

#: The subprocess deadline. Long enough that a cold `git` on Windows is never
#: the reason an arm reddens, short enough that a hung child cannot hold the
#: suite. `_GIT_PROBE_TIMEOUT` covers one git call; `_PYTEST_PROBE_TIMEOUT`
#: covers a whole child collection of the larger suite, measured at about four
#: seconds on this host.
_GIT_PROBE_TIMEOUT = 60.0
_PYTEST_PROBE_TIMEOUT = 300.0

#: The marker file committed into the throwaway repository. Any answer carrying
#: it came from somewhere that is not this repository.
_FOREIGN_MARKER = "FOREIGN_MARKER.txt"

#: Run in a child interpreter. `sys.argv` carries the repository root, the git
#: argv as JSON, whether to import the root conftest first, the stdin to hand
#: git, and the names to report back out of the child's own environment.
#:
#: The conftest import is the ONLY difference between the two halves of every
#: comparison below. Everything else - cwd, argv, stdin, environment - is
#: identical, so a difference in the answer can only have come from it.
_PROBE_SOURCE = """\
import json
import os
import subprocess
import sys

root, argv_json, mode, stdin_text, names_json = sys.argv[1:6]
if mode == "import-conftest":
    sys.path.insert(0, root)
    import conftest  # noqa: F401

completed = subprocess.run(
    json.loads(argv_json),
    cwd=root,
    capture_output=True,
    text=True,
    check=False,
    input=stdin_text,
    timeout=45,
)
sys.stdout.write(
    json.dumps(
        {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr[:400],
            "seen": {name: os.environ.get(name) for name in json.loads(names_json)},
        }
    )
)
"""

#: Run as a pytest plugin inside a child pytest. `pytest_collection_finish`
#: fires AFTER every conftest has been loaded, so what it reads is the
#: environment a test body in that run would see.
#:
#: THE UNSET SENTINEL IS A LITERAL AND NOT `repr(None)`. The value on the other
#: side is a Windows path full of backslashes, and a `repr` round trip made the
#: reader compare an escaped spelling against an unescaped one. A sentinel that
#: cannot be a path keeps the two dispositions apart without any quoting.
_PLUGIN_UNSET = "<no GIT_DIR in the environment>"
_PLUGIN_SOURCE = """\
import os


def pytest_collection_finish(session):
    with open(os.environ["RC_SCRUB_PROBE_OUT"], "w", encoding="utf-8") as handle:
        handle.write(os.environ.get("GIT_DIR", "__UNSET_SENTINEL__") + "\\n")
        handle.write(str(len(session.items)) + "\\n")
""".replace("__UNSET_SENTINEL__", _PLUGIN_UNSET)

#: A test file with no dependency on anything in this repository, planted
#: outside it so the control run loads neither conftest.
_INERT_TEST_SOURCE = """\
def test_nothing():
    assert True
"""


def _base_env() -> dict[str, str]:
    """This process's environment with every scrubbed name removed.

    Taken from `os.environ` rather than from a captured snapshot, and filtered
    anyway. The root conftest has already removed the scrubbed names, so the
    filter is normally a no-op - but an arm elsewhere in the suite is free to set
    one mid-run, and a child that inherited it would grade a tree nobody chose.

    `_COMPANIONS` is filtered here as well even though the conftest does not
    remove it. A baseline computed with `GIT_CONFIG_VALUE_0` ambient would not be
    this repository's clean answer, and every comparison in this file is against
    that baseline.
    """
    drop = set(_SCRUBBED) | set(_COMPANIONS)
    return {k: v for k, v in os.environ.items() if k not in drop}


def _git(argv: list[str], env: dict[str, str], stdin: str | None = None) -> tuple[int, str]:
    """One git call in THIS process, under a deadline, returncode read."""
    require_git_repository()
    completed = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        input=stdin,
        timeout=_GIT_PROBE_TIMEOUT,
    )
    return completed.returncode, completed.stdout


def _clean_answer(argv: list[str], stdin: str | None = None) -> tuple[int, str]:
    """What git says about THIS repository with nothing inherited."""
    return _git(argv, _base_env(), stdin)


def _paths(stdout: str) -> tuple[str, ...]:
    return tuple(part for part in stdout.split(chr(0)) if part)


@pytest.fixture(scope="session")
def probe_script(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The child probe, planted with `write_bytes`.

    `Path.write_text` opens with `newline=None`, which translates every LF to
    CRLF on Windows. A CRLF-carrying probe would still run, but this tree has
    been bitten by that translation often enough that planting source as BYTES
    is the standing shape.
    """
    path = tmp_path_factory.mktemp("git_env_scrub") / "probe.py"
    path.write_bytes(_PROBE_SOURCE.encode("ascii"))
    return path


@pytest.fixture(scope="session")
def foreign_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A throwaway repository tracking exactly one file.

    GLOBAL AND SYSTEM GIT CONFIG ARE CUT OFF, the same way
    `tests/test_hook_gate.py` cuts them off for its own throwaway repo: an
    inherited `core.hooksPath` would point this `git commit` at THIS tree's
    hooks, and `.githooks/pre-push` runs both suites. `--no-verify` on top of
    that is belt and braces, and it is confined to a repository under
    `tmp_path` - never this repository's history.

    ONE FILE, NOT ZERO. An empty foreign repository would make "the corpus
    changed" indistinguishable from "git answered nothing", and the second is
    the disposition every corpus builder in this tree already handles.
    """
    require_git_repository()
    root = tmp_path_factory.mktemp("git_env_scrub_foreign")
    env = _base_env()
    env["GIT_CONFIG_GLOBAL"] = str(root / "no-global-gitconfig")
    env["GIT_CONFIG_SYSTEM"] = str(root / "no-system-gitconfig")

    def run(argv: list[str]) -> None:
        completed = subprocess.run(
            argv,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=_GIT_PROBE_TIMEOUT,
        )
        assert completed.returncode == 0, (
            f"building the throwaway repository failed at {argv!r}: exit "
            f"{completed.returncode}, {completed.stderr.strip()!r}. Every comparison "
            "below needs a second repository that git can actually answer about"
        )

    run(["git", "init", "-q"])
    run(["git", "config", "user.email", "probe@example.invalid"])
    run(["git", "config", "user.name", "Scrub Probe"])
    run(["git", "config", "commit.gpgsign", "false"])
    (root / _FOREIGN_MARKER).write_bytes(b"not this repository\n")
    run(["git", "add", _FOREIGN_MARKER])
    run(["git", "commit", "-q", "--no-verify", "-m", "throwaway"])
    return root


def _run_probe(
    script: Path,
    argv: list[str],
    *,
    exported: dict[str, str],
    import_conftest: bool,
    stdin: str = "",
    log_dir: Path | None = None,
) -> dict[str, object]:
    """Ask a fresh interpreter what git answers, with `exported` already set.

    `RC_LOG_DIR` is pinned so the conftest-importing half honours it instead of
    creating a temporary directory it will never clean up: its own
    `pytest_sessionfinish` cannot run in a child that is not a pytest run.
    """
    env = _base_env()
    env.update(exported)
    if log_dir is not None:
        env["RC_LOG_DIR"] = str(log_dir)
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            str(REPO_ROOT),
            json.dumps(argv),
            "import-conftest" if import_conftest else "plain",
            stdin,
            json.dumps(list(_SCRUBBED)),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=_GIT_PROBE_TIMEOUT,
    )
    assert completed.returncode == 0, (
        f"the child probe itself exited {completed.returncode} rather than answering. "
        f"That is a broken measurement, not a finding: {completed.stderr.strip()[:600]!r}"
    )
    return json.loads(completed.stdout)


# ---------------------------------------------------------------------------
# THE FLOOR. Every comparison below is between two corpora; if the clean one is
# empty or tiny, "unchanged" is satisfied by nothing at all.
# ---------------------------------------------------------------------------


def test_the_clean_corpus_clears_its_floor_and_its_anchors() -> None:
    """This repository, enumerated with nothing inherited, is a real corpus.

    THE FLOOR AND THE ANCHORS ARE TWO DIFFERENT CHECKS. A floor alone passes on
    any repository with enough files in it, including a foreign one; the anchors
    pin that the enumeration is THIS tree. The two conftest files are chosen
    because they are the pair the scrub's placement turns on, so an enumeration
    that lost either is one this file must not build a comparison from.
    """
    returncode, stdout = _clean_answer(["git", "ls-files", "-z"])
    corpus = _paths(stdout)
    assert returncode == 0, (
        f"`git ls-files` exited {returncode} with every scrubbed name absent, so "
        "nothing below is entitled to compare corpora"
    )
    assert len(corpus) >= 50, (
        f"the clean corpus is {len(corpus)} paths. Below that this is not this "
        "repository, and every comparison below would be between two nearly empty "
        f"answers: {sorted(corpus)[:10]}"
    )
    for anchor in ("conftest.py", "tests/conftest.py"):
        assert anchor in corpus, (
            f"{anchor} is not in the clean enumeration, so whatever was enumerated is "
            "not the tree whose conftest carries the scrub"
        )


# ---------------------------------------------------------------------------
# CONSERVATION AGAINST GIT'S OWN LIST. The scrub set is not allowed to be a
# list someone remembered.
# ---------------------------------------------------------------------------
#
# `git rev-parse --local-env-vars` is git's OWN enumeration of the variables
# that are repo-local. The first version of the conftest's tuple covered five of
# the fifteen it names on git 2.53.0.windows.3, and SEVEN of the remaining ten
# were never considered anywhere - GIT_CONFIG, GIT_CONFIG_PARAMETERS,
# GIT_IMPLICIT_WORK_TREE, GIT_GRAFT_FILE, GIT_NO_REPLACE_OBJECTS,
# GIT_REPLACE_REF_BASE and GIT_SHALLOW_FILE.
#
# AN EXPLICIT TUPLE PLUS THIS RECONCILIATION, NOT A DYNAMIC SCRUB. Popping
# whatever git happens to name would be unreviewable: the set would change under
# a git upgrade with no diff anywhere, and it could remove a name a fixture in
# this tree depends on - `tests/test_hook_gate.py` builds a throwaway repository
# whose whole point is a controlled git environment. So the tuple stays written
# down and reviewed, and the RECONCILIATION is what makes a git that gains a
# variable arrive as a red test rather than as an incident.


def _local_env_vars_text() -> str:
    """Git's own list, read from git at runtime."""
    returncode, stdout = _git(["git", "rev-parse", "--local-env-vars"], _base_env())
    assert returncode == 0, (
        f"`git rev-parse --local-env-vars` exited {returncode}, so this file has no "
        "population to reconcile against and must not report a green conservation check"
    )
    return stdout


def _parse_local_env_vars(text: str) -> tuple[str, ...]:
    """One name per line, blanks dropped. Kept separate so it can be fed a
    SYNTHETIC list by the arm that proves this reconciliation can say no."""
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def _unhandled_local_env_vars(
    text: str,
    scrubbed: Sequence[str] = _SCRUBBED,
    kept: Iterable[str] = (),
) -> tuple[str, ...]:
    """Names git calls repo-local that appear in NEITHER table, in git's order.

    `scrubbed` and `kept` are parameters rather than module reads so that the
    non-vacuity arm can hand this function a shrunken table and a git list
    carrying an invented name, and watch it answer.
    """
    handled = set(scrubbed) | set(kept)
    return tuple(name for name in _parse_local_env_vars(text) if name not in handled)


def test_gits_own_local_env_var_list_is_a_real_population() -> None:
    """THE FLOOR under the reconciliation below.

    An empty or truncated `--local-env-vars` makes every conservation check
    below vacuously true, and a vacuous pass is indistinguishable from a real
    one in a summary line. The anchors are the two names whose substitution this
    whole file was written for, so a list that lost either is not the list this
    tree is entitled to reconcile against.
    """
    names = _parse_local_env_vars(_local_env_vars_text())
    assert len(names) >= 10, (
        f"`git rev-parse --local-env-vars` named {len(names)} variables on this git. "
        "Below that this is not git's repo-local enumeration and the conservation "
        f"check would pass over almost nothing: {names}"
    )
    for anchor in ("GIT_DIR", "GIT_INDEX_FILE"):
        assert anchor in names, (
            f"{anchor} is not in git's own repo-local list, so whatever came back is "
            f"not the population this file reconciles against: {names}"
        )


def test_every_name_git_calls_repo_local_is_scrubbed_or_deliberately_kept() -> None:
    """THE CONSERVATION ASSERTION. This is the arm the widening exists for.

    Every name in git's own list must appear in `_GIT_ENV_SCRUBBED` or in
    `_GIT_LOCAL_ENV_KEPT`. A name in neither is a variable nobody decided about:
    either a git upgrade introduced it, or a name was dropped from the tuple by
    hand. Both are the same defect from a reader's point of view - a repo-local
    pointer that can substitute a corpus and that no one has measured.

    IT READS THE CONFTEST'S OWN TABLES, not this file's copies. A scrub list that
    drifted from what the conftest actually pops would otherwise be reconciled
    against itself.
    """
    unhandled = _unhandled_local_env_vars(
        _local_env_vars_text(),
        scrubbed=root_conftest._GIT_ENV_SCRUBBED,
        kept=root_conftest._GIT_LOCAL_ENV_KEPT,
    )
    assert unhandled == (), (
        "git calls these variables repo-local and the root conftest neither scrubs "
        f"them nor records a reason for keeping them: {unhandled}. Measure what each "
        "one does to the queries in this file - reading a RETURNCODE CHANGE AS AN "
        "ANSWER CHANGE wherever the returncode is the answer - then add it to "
        "`_GIT_ENV_SCRUBBED` with a row here, or to `_GIT_LOCAL_ENV_KEPT` with the "
        "measurement that says it is inert"
    )


def test_the_conservation_check_can_say_no() -> None:
    """NON-VACUITY, in both directions that matter, and this is the arm that
    stops the one above from being a shape.

    A reconciliation that returned `()` unconditionally - a typo in the set
    difference, a table read that silently came back empty - would satisfy the
    arm above forever. Two synthetic inputs are fed in here:

      A GIT THAT GAINED A VARIABLE. Git's real output plus one invented name.
      The check must report exactly that name.

      A TABLE THAT LOST A VARIABLE. Git's real output against a scrub tuple with
      `GIT_DIR` removed. The check must report `GIT_DIR`.
    """
    real = _local_env_vars_text()
    kept = tuple(root_conftest._GIT_LOCAL_ENV_KEPT)

    gained = _unhandled_local_env_vars(
        real + "GIT_FUTURE_LOCAL_THING\n",
        scrubbed=root_conftest._GIT_ENV_SCRUBBED,
        kept=kept,
    )
    assert gained == ("GIT_FUTURE_LOCAL_THING",), (
        "a name git does not name today was added to its list and the reconciliation "
        f"did not report it, so it cannot notice a git upgrade at all: {gained}"
    )

    shrunk = tuple(n for n in root_conftest._GIT_ENV_SCRUBBED if n != "GIT_DIR")
    assert len(shrunk) == len(root_conftest._GIT_ENV_SCRUBBED) - 1, (
        "GIT_DIR is no longer in the conftest's scrub tuple, so this arm removed "
        "nothing and measured nothing"
    )
    lost = _unhandled_local_env_vars(real, scrubbed=shrunk, kept=kept)
    assert lost == ("GIT_DIR",), (
        "GIT_DIR was taken out of the scrub tuple and the reconciliation still "
        f"reported nothing unhandled: {lost}"
    )


def test_every_kept_name_is_one_git_actually_calls_repo_local() -> None:
    """The other direction: `_GIT_LOCAL_ENV_KEPT` may not carry a stale name.

    An entry for a variable git does not name is a recorded decision about
    nothing, and it would silently absorb a real name that happened to share the
    spelling later. `_GIT_ENV_SCRUBBED` is deliberately NOT checked this way -
    the four pathspec flags are scrubbed on this tree's own measurement and git
    does not call them repo-local.
    """
    names = set(_parse_local_env_vars(_local_env_vars_text()))
    stale = tuple(sorted(set(root_conftest._GIT_LOCAL_ENV_KEPT) - names))
    assert stale == (), (
        "the root conftest records a keep-decision for variables git does not call "
        f"repo-local: {stale}. Either git dropped them or the name is misspelt"
    )


def test_the_conftest_tuple_and_this_files_copy_are_the_same_list() -> None:
    """The row table below is built from this file's `_SCRUBBED`, and the scrub
    is performed from the conftest's. If the two drift, every row could be
    green about a name the conftest never pops.
    """
    assert tuple(_SCRUBBED) == tuple(root_conftest._GIT_ENV_SCRUBBED)


# ---------------------------------------------------------------------------
# THE INPUT HAS POWER. Without this arm every "unchanged" below could be true
# because the variable does nothing on this machine.
# ---------------------------------------------------------------------------


def test_positive_control_an_exported_git_dir_really_does_swap_the_corpus(
    probe_script: Path, foreign_repo: Path
) -> None:
    """With nothing scrubbing it, `GIT_DIR` substitutes the whole tree at exit 0.

    THE RETURNCODE IS PART OF THE FINDING. A substitution that made git fail
    would be caught by every corpus builder in this tree already, because each
    of them reads the exit code. This one succeeds.
    """
    answer = _run_probe(
        probe_script,
        ["git", "ls-files", "-z"],
        exported={"GIT_DIR": str(foreign_repo / ".git")},
        import_conftest=False,
    )
    corpus = _paths(str(answer["stdout"]))
    assert answer["returncode"] == 0, (
        f"git exited {answer['returncode']} under an exported GIT_DIR, so this arm is "
        "measuring a broken tool rather than the silent substitution it is about"
    )
    assert corpus == (_FOREIGN_MARKER,), (
        "an exported GIT_DIR did not substitute the throwaway repository's index, so "
        "the input this file feeds has no power on this machine and every scrub arm "
        f"below would pass for the wrong reason: {corpus[:10]}"
    )


def test_an_exported_git_dir_does_not_survive_the_root_conftest_import(
    probe_script: Path, foreign_repo: Path, tmp_path: Path
) -> None:
    """The same input, the same child, one extra import - and the tree is back.

    This is the arm the whole file exists for. Remove the scrub from
    `conftest.py` and it reddens with a corpus of exactly one path.
    """
    clean_returncode, clean_stdout = _clean_answer(["git", "ls-files", "-z"])
    answer = _run_probe(
        probe_script,
        ["git", "ls-files", "-z"],
        exported={"GIT_DIR": str(foreign_repo / ".git")},
        import_conftest=True,
        log_dir=tmp_path / "logs",
    )
    corpus = _paths(str(answer["stdout"]))
    # THE CORPUS IS ASSERTED FIRST, DELIBERATELY. The property is about what git
    # answers, not about which names are in an environment, and an arm that
    # reddens on the environment first reports a missing variable where the
    # finding is a substituted tree. Mutating the scrub away must produce the
    # sentence below, naming 1 path against this repository's real count.
    assert (answer["returncode"], corpus) == (clean_returncode, _paths(clean_stdout)), (
        "the corpus a child sees after importing the root conftest is not the corpus "
        "this repository actually tracks, so the substitution survived the scrub: got "
        f"{len(corpus)} paths, expected {len(_paths(clean_stdout))}"
    )
    seen = answer["seen"]
    assert isinstance(seen, dict)
    assert seen["GIT_DIR"] is None, (
        "the corpus came back right but GIT_DIR is still exported, so this tree is "
        f"being described correctly by accident: {seen['GIT_DIR']!r}"
    )


def test_control_nothing_exported_leaves_the_corpus_exactly_where_it_was(
    probe_script: Path, tmp_path: Path
) -> None:
    """NON-VACUITY IN THE OTHER DIRECTION: the scrub does not damage a clean run.

    A scrub that emptied the corpus, or that broke git, would satisfy every
    "did not survive" assertion above. Here nothing is exported and the answer
    must be byte-identical to this process's own.
    """
    clean_returncode, clean_stdout = _clean_answer(["git", "ls-files", "-z"])
    answer = _run_probe(
        probe_script,
        ["git", "ls-files", "-z"],
        exported={},
        import_conftest=True,
        log_dir=tmp_path / "logs",
    )
    assert (answer["returncode"], answer["stdout"]) == (clean_returncode, clean_stdout), (
        "importing the root conftest changed what git says about this tree even with "
        "nothing inherited, so the scrub is doing something other than removing an "
        "inherited value"
    )


# ---------------------------------------------------------------------------
# THE TABLE. One row per scrubbed variable, each carrying the query it was
# MEASURED to change and its own positive control.
# ---------------------------------------------------------------------------

_LS_FILES = ["git", "ls-files", "-z"]
_LS_FILES_GLOB = ["git", "ls-files", "-z", "--", "tests/test_line*.py"]
_LS_FILES_ICASE = ["git", "ls-files", "-z", "--", "TESTS/TEST_LINE_ENDINGS.PY"]
_LS_TREE = ["git", "ls-tree", "-r", "--name-only", "HEAD"]
_CHECK_IGNORE = ["git", "check-ignore", "-v", "--stdin"]
_CHECK_IGNORE_STDIN = "logs/probe.log\ntests/conftest.py\n"

#: THE RETURNCODE IS THE ANSWER HERE, and that is the point of the row that uses
#: it. `check-ignore -q` prints nothing at all: 0 means ignored and 1 means not.
#: `tests/test_agent_roster.py` returns exactly this comparison as its corpus and
#: `tests/test_ci_workflow_complement.py` asserts on this exit code in both
#: halves of its ignore guard. The first version of the conftest's scrub list was
#: built by keeping only variables that changed an answer AT EXIT 0, which is
#: structurally blind to every query of this shape - and GIT_CONFIG_PARAMETERS,
#: which git exports to hooks itself, was discarded by exactly that filter.
_CHECK_IGNORE_Q = ["git", "check-ignore", "-q", "--no-index", "core/probe_not_ignored.json"]

#: `tests/test_commit_trailers.py`'s own two queries. The first is its corpus -
#: every commit in the history - and the second is the gate it gives up on.
_LOG_HISTORY = ["git", "log", "--format=%H"]
_IS_SHALLOW = ["git", "rev-parse", "--is-shallow-repository"]

#: `git config --list`, which is where an inherited `GIT_CONFIG` lands. It is
#: not a corpus builder in this tree's census, but `tests/test_hook_gate.py`
#: reads `git config --get core.hooksPath` and asserts it is EMPTY, and an
#: empty answer is exactly what a substituted config file gives away for free.
_CONFIG_LIST = ["git", "config", "--list"]

#: (variable, value kind, git argv, stdin). The value kind says how to build a
#: hostile environment for the row, because the fourteen names take paths,
#: flags, a config file, a config-parameter string and a history-truncating
#: file between them.
_ROWS: tuple[tuple[str, str, list[str], str], ...] = (
    ("GIT_DIR", "git-dir", _LS_FILES, ""),
    ("GIT_INDEX_FILE", "index", _LS_FILES, ""),
    ("GIT_WORK_TREE", "work-tree", _CHECK_IGNORE, _CHECK_IGNORE_STDIN),
    ("GIT_COMMON_DIR", "git-dir", _LS_TREE, ""),
    ("GIT_OBJECT_DIRECTORY", "objects", _LS_TREE, ""),
    ("GIT_CONFIG", "config-file", _CONFIG_LIST, ""),
    ("GIT_CONFIG_PARAMETERS", "config-parameters", _CHECK_IGNORE_Q, ""),
    ("GIT_CONFIG_COUNT", "config-count", _CHECK_IGNORE_Q, ""),
    ("GIT_GRAFT_FILE", "history-file", _LOG_HISTORY, ""),
    ("GIT_SHALLOW_FILE", "history-file", _IS_SHALLOW, ""),
    ("GIT_LITERAL_PATHSPECS", "flag", _LS_FILES_GLOB, ""),
    ("GIT_NOGLOB_PATHSPECS", "flag", _LS_FILES_GLOB, ""),
    ("GIT_GLOB_PATHSPECS", "flag", _CHECK_IGNORE, _CHECK_IGNORE_STDIN),
    ("GIT_ICASE_PATHSPECS", "flag", _LS_FILES_ICASE, ""),
)


@pytest.fixture(scope="session")
def hostile_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """The files a hostile value has to point AT, built once.

    THE GRAFT AND SHALLOW FILES CARRY THIS REPOSITORY'S OWN HEAD. A graft file
    naming HEAD with no parents makes git report a one-commit history at EXIT 0,
    which is the whole finding: `tests/test_commit_trailers.py` would grade one
    commit and report green over a history it never read. Planted with
    `write_bytes` because `Path.write_text` translates LF to CRLF on Windows and
    git reads these files line by line.

    THE EXCLUDES FILE IGNORES `core/`, which is what makes the `check-ignore -q`
    rows flip: `core/probe_not_ignored.json` is NOT ignored by this repository's
    own `.gitignore`, so rc 1 is the clean answer and rc 0 is the substituted
    one.
    """
    require_git_repository()
    root = tmp_path_factory.mktemp("git_env_scrub_hostile")

    excludes = root / "hostile-excludes.txt"
    excludes.write_bytes(b"core/\ndata/cache/\ntests/\n")

    config = root / "hostile.gitconfig"
    config.write_bytes(
        ("[core]\n\texcludesFile = " + excludes.as_posix() + "\n").encode("ascii")
    )

    returncode, stdout = _clean_answer(["git", "rev-parse", "HEAD"])
    head = stdout.strip()
    assert returncode == 0 and len(head) >= 40, (
        f"`git rev-parse HEAD` exited {returncode} with {head!r}, so the graft and "
        "shallow rows cannot be built and would silently feed an inert file"
    )
    history = root / "truncate-history.txt"
    history.write_bytes((head + "\n").encode("ascii"))

    return {
        "excludes": excludes.as_posix(),
        "config": str(config),
        "history": str(history),
    }


def _row_exports(name: str, kind: str, foreign: Path, hostile: dict[str, str]) -> dict[str, str]:
    """The whole environment a row exports, not just one value.

    `GIT_CONFIG_COUNT` is the reason this returns a mapping. Git reads the count
    FIRST and ignores `GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n` without it, so
    the row exports all three and the scrubbed half leaves the key and value
    behind. That half is the measurement behind the conftest's claim that
    scrubbing the count alone is sufficient - not a restatement of it.
    """
    if kind == "config-count":
        return {
            name: "1",
            "GIT_CONFIG_KEY_0": "core.excludesfile",
            "GIT_CONFIG_VALUE_0": hostile["excludes"],
        }
    value = {
        "git-dir": str(foreign / ".git"),
        "index": str(foreign / ".git" / "index"),
        "objects": str(foreign / ".git" / "objects"),
        "work-tree": str(foreign),
        "flag": "1",
        "config-file": hostile["config"],
        "config-parameters": "'core.excludesfile'='" + hostile["excludes"] + "'",
        "history-file": hostile["history"],
    }[kind]
    return {name: value}


def test_the_table_covers_every_name_the_root_conftest_removes() -> None:
    """The rows and the scrub list are the same set.

    A row deleted from `_ROWS` would silently retire a measurement while every
    surviving row stayed green, and a name added to the conftest's tuple with no
    row would be scrubbed on nobody's evidence. This is the one arm here that
    compares two lists rather than feeding an input, and it exists to stop the
    input-feeding table from quietly shrinking.
    """
    assert tuple(row[0] for row in _ROWS) == _SCRUBBED


@pytest.mark.parametrize(
    ("name", "kind", "argv", "stdin"), _ROWS, ids=[row[0] for row in _ROWS]
)
def test_every_variable_measured_to_swap_an_answer_is_scrubbed(
    probe_script: Path,
    foreign_repo: Path,
    hostile_artifacts: dict[str, str],
    tmp_path: Path,
    name: str,
    kind: str,
    argv: list[str],
    stdin: str,
) -> None:
    """Two measurements per row, and the first is what stops the second lying.

    UNSCRUBBED, the exported value must CHANGE this query's answer. A row whose
    variable turned out to be inert on this git would pass the second half
    trivially, and the table would grow rows that measure nothing - which is
    exactly the failure this tree has already shipped.

    SCRUBBED, the same query must answer exactly what this process gets with
    nothing inherited.

    BOTH HALVES COMPARE THE PAIR (returncode, stdout), and that is the corrected
    criterion rather than a stylistic choice. Three rows here - the two config
    rows and `GIT_WORK_TREE` - change nothing but the exit code, because the
    query they reach reports its answer THROUGH the exit code. A comparison that
    looked only at stdout would find those rows inert and a filter built on one
    would never have added them.
    """
    exported = _row_exports(name, kind, foreign_repo, hostile_artifacts)
    baseline_returncode, baseline_stdout = _clean_answer(argv, stdin or None)

    loose = _run_probe(
        probe_script, argv, exported=exported, import_conftest=False, stdin=stdin
    )
    assert (loose["returncode"], loose["stdout"]) != (baseline_returncode, baseline_stdout), (
        f"exporting {exported!r} did not change `{' '.join(argv)}` on this git, so "
        "this row feeds an input with no power and its scrub half proves nothing. "
        "Re-derive the query this variable actually reaches, or drop the row from the "
        "conftest's tuple as well as from here"
    )

    scrubbed = _run_probe(
        probe_script,
        argv,
        exported=exported,
        import_conftest=True,
        stdin=stdin,
        log_dir=tmp_path / "logs",
    )
    # The ANSWER first and the environment second, for the reason given at
    # `test_an_exported_git_dir_does_not_survive_the_root_conftest_import`.
    assert (scrubbed["returncode"], scrubbed["stdout"]) == (
        baseline_returncode,
        baseline_stdout,
    ), (
        f"with {name} exported, `{' '.join(argv)}` still answered differently after the "
        "root conftest was imported, so the scrub did not restore this tree's own answer"
    )
    seen = scrubbed["seen"]
    assert isinstance(seen, dict)
    assert seen[name] is None, (
        f"the answer matched but {name} is still exported, so this query is agreeing "
        f"with the clean one by accident: {seen[name]!r}"
    )


# ---------------------------------------------------------------------------
# BOTH SUITES, UNDER A REAL PYTEST RUN.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def plugin_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A directory holding the reporting plugin, planted as bytes."""
    root = tmp_path_factory.mktemp("git_env_scrub_plugin")
    (root / "rc_scrub_probe.py").write_bytes(_PLUGIN_SOURCE.encode("ascii"))
    return root


def _collect_under_exported_git_dir(
    plugin_dir: Path, target: Path, cwd: Path, foreign_git: Path, out: Path
) -> tuple[int, str | None, int | None]:
    """Run a child pytest over `target` with `GIT_DIR` exported.

    Returns the child's exit code and what the plugin saw at
    `pytest_collection_finish`, which is after every conftest has been loaded.
    """
    env = _base_env()
    env["GIT_DIR"] = str(foreign_git)
    env["PYTHONPATH"] = str(plugin_dir)
    env["RC_SCRUB_PROBE_OUT"] = str(out)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(target),
            "--collect-only",
            "-p",
            "rc_scrub_probe",
            "-p",
            "no:cacheprovider",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=_PYTEST_PROBE_TIMEOUT,
    )
    if not out.exists():
        return completed.returncode, "<the plugin never reported>", None
    lines = out.read_text(encoding="utf-8").splitlines()
    reported = lines[0] if lines else ""
    collected = int(lines[1]) if len(lines) > 1 else None
    return completed.returncode, None if reported == _PLUGIN_UNSET else reported, collected


@pytest.mark.parametrize("suite", ["tests", "agents/pity_engine"])
def test_the_scrub_reaches_both_suites_under_a_real_pytest_run(
    plugin_dir: Path, tmp_path: Path, foreign_repo: Path, suite: str
) -> None:
    """A real `python -m pytest <suite>` with `GIT_DIR` already exported.

    `agents/pity_engine` IS THE ROW THAT DECIDES WHERE THE SCRUB LIVES.
    `tests/conftest.py` is never loaded for it, so a scrub placed there passes
    the `tests` row and reddens this one. Measured before the scrub existed:
    both rows saw the foreign `GIT_DIR`, and the `tests` row additionally exited
    2 with `Interrupted: 1 error during collection`.
    """
    returncode, reported, collected = _collect_under_exported_git_dir(
        plugin_dir,
        REPO_ROOT / suite,
        REPO_ROOT,
        foreign_repo / ".git",
        tmp_path / "reported.txt",
    )
    assert reported is None, (
        f"collecting {suite} with GIT_DIR exported left it set to {reported!r}, so every "
        "guard in that suite would grade a tree nobody chose"
    )
    assert returncode == 0, (
        f"collecting {suite} with GIT_DIR exported exited {returncode} rather than 0. "
        "The variable is gone from the environment but something else in that run is "
        "still reading it"
    )
    assert collected is not None and collected > 0, (
        f"{suite} collected {collected} tests, so a green result there says nothing"
    )


def test_control_the_plugin_reports_git_dir_when_no_conftest_of_ours_is_loaded(
    plugin_dir: Path, tmp_path: Path, foreign_repo: Path
) -> None:
    """THE REPORTING MECHANISM CAN SAY YES.

    Without this, a plugin that always wrote `None` - a typo, a shadowed name,
    an `os.environ` read that never happens - would satisfy both rows above
    while measuring nothing. The same plugin is pointed at an inert test file
    OUTSIDE this repository, where neither conftest is loaded, and `GIT_DIR`
    must come back intact.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "test_inert.py").write_bytes(_INERT_TEST_SOURCE.encode("ascii"))
    foreign_git = foreign_repo / ".git"
    returncode, reported, collected = _collect_under_exported_git_dir(
        plugin_dir, outside, outside, foreign_git, tmp_path / "reported.txt"
    )
    assert returncode == 0, f"the control collection exited {returncode}"
    assert collected == 1, f"the control collected {collected} tests rather than 1"
    assert reported == str(foreign_git), (
        "the control run did not report the GIT_DIR it was given, so the plugin cannot "
        f"distinguish a scrubbed run from an unscrubbed one: {reported!r}"
    )
