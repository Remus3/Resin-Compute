"""An INHERITED git environment must not decide what this tree tracks.

WHAT IS GUARDED, AND WHY IT IS NOT A SHAPE.

`conftest.py` at the repository root removes nine git environment variables at
IMPORT. Every arm below FEEDS ONE OF THEM AS A REAL INPUT to a child process and
then measures the answer a corpus builder would get. Nothing here asserts that a
fixture exists, that a tuple has nine entries, or that a name appears in a file.
A shape arm pins format and not input, and this tree has shipped four of those
in one day that stayed green against a mutant which broke the property.

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

  THE CLEAN CORPUS is what `git ls-files` says about this repository with the
  nine variables absent. `test_the_clean_corpus_clears_its_floor_and_its_anchors`
  is the floor: empty it and that arm reddens before any comparison below can be
  satisfied vacuously.

  THE FOREIGN CORPUS is a throwaway repository holding one file. It exists so
  that "the answer changed" is a difference a reader can see rather than an
  inequality between two opaque blobs.

  THE PER-VARIABLE ANSWERS are five different git queries, because the nine
  variables do not all reach the same one. `GIT_DIR` swaps `ls-files`;
  `GIT_WORK_TREE` leaves `ls-files` alone and moves `check-ignore`;
  `GIT_OBJECT_DIRECTORY` reaches only `ls-tree`. A table that probed `ls-files`
  for all nine would have six rows that measure nothing and would still be
  green, so each row carries the query its variable was MEASURED to change, and
  each row asserts that change before asserting the scrub removes it.

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
from pathlib import Path

import pytest

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
    "GIT_LITERAL_PATHSPECS",
    "GIT_NOGLOB_PATHSPECS",
    "GIT_GLOB_PATHSPECS",
    "GIT_ICASE_PATHSPECS",
)

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
    anyway. The root conftest has already removed these nine, so the filter is
    normally a no-op - but an arm elsewhere in the suite is free to set one
    mid-run, and a child that inherited it would grade a tree nobody chose.
    """
    return {k: v for k, v in os.environ.items() if k not in _SCRUBBED}


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
        f"`git ls-files` exited {returncode} with the nine scrubbed names absent, so "
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

#: (variable, value kind, git argv, stdin). The value kind says how to build a
#: hostile value from the throwaway repository, because four of the nine take a
#: path and five take a flag.
_ROWS: tuple[tuple[str, str, list[str], str], ...] = (
    ("GIT_DIR", "git-dir", _LS_FILES, ""),
    ("GIT_INDEX_FILE", "index", _LS_FILES, ""),
    ("GIT_WORK_TREE", "work-tree", _CHECK_IGNORE, _CHECK_IGNORE_STDIN),
    ("GIT_COMMON_DIR", "git-dir", _LS_TREE, ""),
    ("GIT_OBJECT_DIRECTORY", "objects", _LS_TREE, ""),
    ("GIT_LITERAL_PATHSPECS", "flag", _LS_FILES_GLOB, ""),
    ("GIT_NOGLOB_PATHSPECS", "flag", _LS_FILES_GLOB, ""),
    ("GIT_GLOB_PATHSPECS", "flag", _CHECK_IGNORE, _CHECK_IGNORE_STDIN),
    ("GIT_ICASE_PATHSPECS", "flag", _LS_FILES_ICASE, ""),
)


def _row_value(kind: str, foreign: Path) -> str:
    return {
        "git-dir": str(foreign / ".git"),
        "index": str(foreign / ".git" / "index"),
        "objects": str(foreign / ".git" / "objects"),
        "work-tree": str(foreign),
        "flag": "1",
    }[kind]


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
    """
    value = _row_value(kind, foreign_repo)
    baseline_returncode, baseline_stdout = _clean_answer(argv, stdin or None)

    loose = _run_probe(
        probe_script, argv, exported={name: value}, import_conftest=False, stdin=stdin
    )
    assert (loose["returncode"], loose["stdout"]) != (baseline_returncode, baseline_stdout), (
        f"exporting {name}={value!r} did not change `{' '.join(argv)}` on this git, so "
        "this row feeds an input with no power and its scrub half proves nothing. "
        "Re-derive the query this variable actually reaches, or drop the row from the "
        "conftest's tuple as well as from here"
    )

    scrubbed = _run_probe(
        probe_script,
        argv,
        exported={name: value},
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
