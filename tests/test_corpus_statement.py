"""Arms for `tools/corpus_statement.py`.

WHY THIS MODULE EXISTS. Three guards in this tree build their corpus from
`git ls-files`, so a file present on disk but NOT YET TRACKED is invisible to
them BY CONSTRUCTION. Measured in this tree: a new test module passed the
builder's suite run AND the merge-seam run, then the pre-push gate refused it
the moment it was committed. Both green runs were VACUOUS for that file and
NOTHING SAID SO. The cost was the SILENCE, not the untrackedness.

THE LOAD-BEARING DISTINCTION, and the reason arm 2 exists at all:
"untracked" and "gitignored" are DIFFERENT SETS.

  git ls-files --others                      untracked INCLUDING ignored
  git ls-files --others --exclude-standard   untracked AND NOT ignored

`moon_sync_inbox/` is gitignored and holds hundreds of files. A helper built on
the first form would report it on every single run, the warning would be
suppressed as noise, and the whole slice would have failed. Arm 2 is what keeps
that directory out.

Every arm builds a THROWAWAY repository under `tmp_path`. Nothing here touches
the real working tree, and every git call is pinned to `cwd=<tmp_path>`.
"""

from __future__ import annotations

import ast
import logging
import re
import subprocess
import textwrap
from pathlib import Path

import pytest

from tests.conftest import require_git_repository
from tools import corpus_statement
from tools.corpus_statement import untracked_not_ignored


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git inside the throwaway repo, never anywhere else."""
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def _throwaway_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "throwaway"
    repo.mkdir(parents=True)
    _git(repo, "init")
    return repo


def _plain_ls_files(repo: Path) -> list[str]:
    """The corpus the three real guards actually build - tracked files only."""
    out = _git(repo, "ls-files", "-z").stdout
    return sorted(p for p in out.split("\0") if p)


def test_untracked_not_ignored_names_a_file_git_ls_files_cannot_see(
    tmp_path: Path,
) -> None:
    """The defect arm: the blind spot is named, and it is really a blind spot.

    Two assertions, because one alone proves nothing. The first pins that plain
    `git ls-files` genuinely MISSES the new file - without it the arm could pass
    against a corpus that was never blind. The second pins that the helper
    FINDS it.
    """
    repo = _throwaway_repo(tmp_path)

    (repo / "tracked.py").write_text("# already in the index\n", encoding="utf-8")
    _git(repo, "add", "tracked.py")

    (repo / "new_module.py").write_text("# written, never staged\n", encoding="utf-8")

    corpus = _plain_ls_files(repo)
    assert corpus == ["tracked.py"]
    assert "new_module.py" not in corpus, (
        "premise broken: plain `git ls-files` was supposed to be blind here"
    )

    assert untracked_not_ignored(repo) == ["new_module.py"]


def test_a_gitignored_path_is_not_reported(tmp_path: Path) -> None:
    """The arm that keeps `moon_sync_inbox/` out of the warning.

    Paired guards, per this tree's sweep convention: one asserts the ignored
    path is GONE, one asserts the legitimate untracked neighbour SURVIVED. An
    implementation that reported nothing at all would score 100 percent on the
    first assertion, so the second is what makes the first mean something.
    """
    repo = _throwaway_repo(tmp_path)

    (repo / ".gitignore").write_text("noisy_inbox/\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")

    noisy = repo / "noisy_inbox"
    noisy.mkdir()
    (noisy / "note_one.md").write_text("ignored\n", encoding="utf-8")
    (noisy / "note_two.md").write_text("ignored\n", encoding="utf-8")

    (repo / "real_new_file.py").write_text("# untracked, not ignored\n", encoding="utf-8")

    found = untracked_not_ignored(repo)

    assert not [p for p in found if p.startswith("noisy_inbox/")], (
        f"a gitignored path reached the warning: {found}"
    )
    assert "real_new_file.py" in found, (
        "the ignored set was excluded by excluding everything - vacuous"
    )


def test_a_git_failure_is_logged_and_never_a_silent_empty(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A silent empty is the exact vacuity shape this module exists to expose.

    Two failure MODES, because they take different code paths: a directory that
    does not exist fails before git runs at all (OSError from subprocess), while
    a corrupt `.git` makes git itself exit non-zero. Both must log and both must
    return [].
    """
    missing = tmp_path / "no_such_directory"

    with caplog.at_level(logging.ERROR, logger="tools.corpus_statement"):
        result = untracked_not_ignored(missing)
    assert result == []
    assert caplog.records, "returned [] without logging - a silent empty"
    assert "no_such_directory" in caplog.text

    caplog.clear()

    corrupt = tmp_path / "corrupt"
    corrupt.mkdir()
    (corrupt / ".git").write_text("this is not a valid gitfile\n", encoding="utf-8")

    with caplog.at_level(logging.ERROR, logger="tools.corpus_statement"):
        result = untracked_not_ignored(corrupt)
    assert result == []
    assert caplog.records, "returned [] without logging - a silent empty"


def test_a_healthy_repo_logs_no_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Non-vacuity for the arm above: the detector is not simply always firing."""
    repo = _throwaway_repo(tmp_path)
    (repo / "some_file.py").write_text("# untracked\n", encoding="utf-8")

    with caplog.at_level(logging.ERROR, logger="tools.corpus_statement"):
        result = untracked_not_ignored(repo)

    assert result == ["some_file.py"]
    assert not caplog.records, f"logged an error on a healthy repo: {caplog.text}"


def test_result_is_sorted_and_uses_forward_slashes(tmp_path: Path) -> None:
    """Deterministic order and POSIX separators, including on Windows.

    `Path` renders a backslash separator on this host, so an implementation that
    joined paths itself would emit `nested\\deep\\b_file.py` and the membership
    assertion below would fail. git's own `-z` output is already forward-slash,
    which is why the helper must pass it through rather than re-derive it.
    """
    repo = _throwaway_repo(tmp_path)

    nested = repo / "nested" / "deep"
    nested.mkdir(parents=True)
    (nested / "b_file.py").write_text("# b\n", encoding="utf-8")
    (repo / "z_file.py").write_text("# z\n", encoding="utf-8")
    (repo / "a_file.py").write_text("# a\n", encoding="utf-8")

    found = untracked_not_ignored(repo)

    assert found == sorted(found)
    assert found == ["a_file.py", "nested/deep/b_file.py", "z_file.py"]
    assert not any("\\" in p for p in found)


def test_the_helper_sorts_output_git_handed_it_out_of_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The sort is armed against DELETION, which a real repo cannot do.

    `test_result_is_sorted_and_uses_forward_slashes` above cannot fail if
    `sorted()` is replaced by `list()`: measured, that mutant SURVIVED the whole
    module at 11 passed. The cause is that `git ls-files` already emits paths in
    sorted order, so on any real fixture the two agree and the arm is a
    statement about git's incidental behaviour rather than about this code.

    Feeding deliberately out-of-order bytes through a stubbed `subprocess.run`
    is the only way to separate the two. This arm kills the pass-through mutant;
    the fixture-based arm above keeps its own job of pinning the forward-slash
    separators that git really does produce.
    """

    class _FakeCompleted:
        returncode = 0
        stdout = b"z_file.py\0a_file.py\0m_file.py\0"
        stderr = b""

    def _fake_run(*args: object, **kwargs: object) -> _FakeCompleted:
        return _FakeCompleted()

    monkeypatch.setattr(corpus_statement.subprocess, "run", _fake_run)

    assert corpus_statement.untracked_not_ignored(tmp_path) == [
        "a_file.py",
        "m_file.py",
        "z_file.py",
    ]


def test_undecodable_bytes_survive_the_decode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`surrogateescape` keeps a bad byte round-trippable; `replace` destroys it.

    A real git call cannot reach this. Measured on this host: a filename holding
    lone surrogates IS creatable, but git sanitises the path to U+FFFD before
    emitting, so its `-z` output is always valid UTF-8 and both decodings agree.
    The stub is the only way to separate them - the same technique, and the same
    justification, as the sort arm above.

    The distinction is not cosmetic. Under `replace` every undecodable byte
    collapses to the same character, so two genuinely different unscanned files
    can be reported under one name - a corpus statement that silently merges its
    own subjects.
    """

    class _FakeCompleted:
        returncode = 0
        stdout = b"bad_\xff_byte.py\0"
        stderr = b""

    def _fake_run(*args: object, **kwargs: object) -> _FakeCompleted:
        return _FakeCompleted()

    monkeypatch.setattr(corpus_statement.subprocess, "run", _fake_run)

    found = corpus_statement.untracked_not_ignored(tmp_path)

    assert found == ["bad_" + chr(0xDCFF) + "_byte.py"]
    assert found[0].encode("utf-8", "surrogateescape") == b"bad_\xff_byte.py"
    # chr(), not a literal: U+FFFD is itself a non-ASCII byte, so spelling it
    # directly would make this file violate the ASCII arm below - which is
    # exactly what it did on the first attempt, and what that arm caught.
    assert chr(0xFFFD) not in found[0], "the byte was destroyed rather than preserved"


def test_prefixes_narrows_the_corpus_without_hiding_the_rest(tmp_path: Path) -> None:
    """`prefixes` is a filter for a guard that only owns part of the tree.

    Paired again: one assertion that the out-of-scope path is filtered OUT, one
    that the in-scope path is still IN. A filter that returned [] would pass the
    first on its own.
    """
    repo = _throwaway_repo(tmp_path)

    (repo / "tests").mkdir()
    (repo / "docs").mkdir()
    (repo / "tests" / "test_new.py").write_text("# new arm\n", encoding="utf-8")
    (repo / "docs" / "note.md").write_text("# note\n", encoding="utf-8")

    found = untracked_not_ignored(repo, prefixes=["tests/"])

    assert "tests/test_new.py" in found
    assert "docs/note.md" not in found

    unfiltered = untracked_not_ignored(repo)
    assert "docs/note.md" in unfiltered, "the unfiltered corpus lost a file"


def test_an_exported_git_work_tree_does_not_hijack_the_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The result must describe `root`, not an ambient work tree.

    MEASURED, not assumed. Of the three git env vars this module scrubs, only
    `GIT_WORK_TREE` actually redirects THIS command - `GIT_DIR` and
    `GIT_INDEX_FILE` leave it answering about `cwd`. An earlier revision armed
    `GIT_DIR`, which meant the arm passed whether or not the scrub existed:
    deleting the entire scrub left the module's eight arms at 8 passed. An arm
    that has never rejected anything is not a gate.

    The hijack is SILENT - returncode 0, empty stderr - so there is no failure
    signal to fall back on. The caller simply receives the decoy's untracked
    files as a statement about `root`: a corpus statement about the wrong
    corpus, strictly worse than the silence this module exists to abolish.

    The premise assertion below runs the RAW command, without the helper, to
    prove the hijack is real on this host's git. Without it a future git that
    stopped honouring `GIT_WORK_TREE` would leave this arm green while testing
    nothing - the same no-op failure, one version later.
    """
    repo = _throwaway_repo(tmp_path)
    (repo / "tracked.py").write_text("# tracked\n", encoding="utf-8")
    _git(repo, "add", "tracked.py")
    (repo / "real_answer.py").write_text("# in root\n", encoding="utf-8")

    decoy = _throwaway_repo(tmp_path / "elsewhere")
    (decoy / "decoy_answer.py").write_text("# in the decoy\n", encoding="utf-8")

    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))

    unscrubbed = subprocess.run(
        ["git", "ls-files", "-z", "--others", "--exclude-standard"],
        cwd=repo,
        capture_output=True,
        check=True,
    ).stdout.decode()
    assert "decoy_answer.py" in unscrubbed, (
        "premise broken: GIT_WORK_TREE no longer hijacks this command, so this "
        "arm would pass with the scrub deleted - re-derive which vars redirect"
    )

    found = untracked_not_ignored(repo)

    assert found == ["real_answer.py"]
    assert "decoy_answer.py" not in found


@pytest.mark.parametrize("var", ["GIT_DIR", "GIT_INDEX_FILE"])
def test_an_exported_git_dir_or_index_does_not_hijack_the_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, var: str
) -> None:
    """These two hijack in a different SHAPE, and only when a tracked file exists.

    `--others` lists the work tree MINUS the index. Substituting the index via
    `GIT_DIR` or `GIT_INDEX_FILE` therefore makes a file that IS tracked come
    back as UNTRACKED - a false "this was not scanned" claim, which is exactly
    this module's subject. rc 0, empty stderr, no signal.

    THE FIXTURE IS THE ARM. An earlier revision measured these two in a repo
    with NO TRACKED FILES, found them inert, and wrote into the module that no
    arm for them could exist. With an empty index there is nothing to relabel,
    so the defect was excluded by the fixture rather than absent - the recorded
    trap. `tracked.py` below is the difference between this arm working and
    this arm being theatre.
    """
    repo = _throwaway_repo(tmp_path)
    (repo / "tracked.py").write_text("# tracked\n", encoding="utf-8")
    _git(repo, "add", "tracked.py")
    (repo / "untracked.py").write_text("# untracked\n", encoding="utf-8")

    decoy = _throwaway_repo(tmp_path / "elsewhere")

    value = str(decoy / ".git") if var == "GIT_DIR" else str(decoy / ".git" / "index")
    monkeypatch.setenv(var, value)

    unscrubbed = subprocess.run(
        ["git", "ls-files", "-z", "--others", "--exclude-standard"],
        cwd=repo,
        capture_output=True,
        check=True,
    ).stdout.decode()
    assert "tracked.py" in unscrubbed, (
        f"premise broken: {var} no longer relabels a tracked file as untracked, "
        "so this arm would pass with the scrub deleted - re-derive the matrix "
        "WITH A TRACKED FILE PRESENT before trusting any inertness claim"
    )

    assert untracked_not_ignored(repo) == ["untracked.py"]


def test_an_empty_prefix_sequence_warns_and_returns_the_unfiltered_corpus(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """`prefixes=[]` warns and filters nothing. It must NEVER raise.

    An earlier revision raised `ValueError` on the ambiguity between "no filter"
    and "match nothing". The ambiguity is real; raising is still wrong. The
    natural caller wiring is a comprehension over owned directories, which
    yields `[]` on a shallow checkout or an empty config key. A raise there
    escapes into `tools/precommit_gate.py` and out of a git hook as a non-zero
    exit, converting this warn-and-pass mechanism into the refusing gate the
    adjudicated ruling forbids.

    Over-naming in a warning is harmless; under-naming reproduces the original
    silence. The unfiltered set is therefore the safe guess, and it is said out
    loud.
    """
    repo = _throwaway_repo(tmp_path)
    (repo / "docs").mkdir()
    (repo / "docs" / "note.md").write_text("# note\n", encoding="utf-8")
    (repo / "root_file.py").write_text("# root\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="tools.corpus_statement"):
        result = untracked_not_ignored(repo, prefixes=[])

    assert result == ["docs/note.md", "root_file.py"]
    assert result == untracked_not_ignored(repo), "empty prefixes must not filter"
    assert caplog.records, "returned the unfiltered corpus in silence"
    assert "empty prefix sequence" in caplog.text


def test_a_backslash_prefix_is_normalised_rather_than_silently_empty(
    tmp_path: Path,
) -> None:
    """This is Windows, and the helper returns forward slashes.

    A caller who builds a prefix from a `Path` hands over `tests\\`, which
    would match none of the forward-slash paths and return a silent empty. The
    control below pins that the forward-slash spelling finds the same file, so
    the arm cannot pass by both spellings returning nothing.
    """
    repo = _throwaway_repo(tmp_path)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_new.py").write_text("# new arm\n", encoding="utf-8")

    forward = untracked_not_ignored(repo, prefixes=["tests/"])
    assert forward == ["tests/test_new.py"]

    backslash = untracked_not_ignored(repo, prefixes=["tests\\"])
    assert backslash == forward


def test_a_prefix_naming_a_missing_directory_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A prefix that can never match is a caller typo, and is said out loud.

    Deliberately keyed to the directory EXISTING, not to the match count: on a
    tree with no untracked files every prefix matches nothing, and a warning
    that fires on every healthy run is one a reader learns to suppress. The
    second half of this arm pins that silence.
    """
    repo = _throwaway_repo(tmp_path)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_new.py").write_text("# new arm\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="tools.corpus_statement"):
        result = untracked_not_ignored(repo, prefixes=["no_such_dir/"])
    assert result == []
    assert caplog.records, "a prefix that can never match returned [] in silence"
    assert "no_such_dir/" in caplog.text

    caplog.clear()

    with caplog.at_level(logging.WARNING, logger="tools.corpus_statement"):
        assert untracked_not_ignored(repo, prefixes=["tests/"]) == ["tests/test_new.py"]
    assert not caplog.records, f"warned about a real directory: {caplog.text}"


def test_this_module_is_seven_bit_ascii() -> None:
    """The tree's standing rule, checked on the two files this slice authored.

    Built with `chr()` rather than a literal: typing a banned glyph into the
    test that bans it makes the test violate its own rule.
    """
    banned = {
        chr(0x2014): "em-dash",
        chr(0x2013): "en-dash",
        chr(0x2018): "left single quote",
        chr(0x2019): "right single quote",
        chr(0x201C): "left double quote",
        chr(0x201D): "right double quote",
    }
    here = Path(__file__).resolve()
    module = here.parent.parent / "tools" / "corpus_statement.py"

    for path in (here, module):
        assert path.exists(), path
        raw = path.read_bytes()
        try:
            raw.decode("ascii")
        except UnicodeDecodeError as exc:  # pragma: no cover - only on a defect
            pytest.fail(f"{path.name} is not 7-bit ASCII: {exc}")
        text = raw.decode("ascii")
        for glyph, name in banned.items():
            assert glyph not in text, f"{path.name} contains a {name}"


# ---------------------------------------------------------------------------
# THE CALLER-CLAIM ORACLE.
#
# `tools/corpus_statement.py` has NO production caller, and until 2026-10-02
# its docstrings said four times over that the glyph gate invoked it. That was
# false the whole time. The correction was verified by a scratchpad oracle
# which was never committed - and an uncommitted oracle is the same shape as
# the defect it caught. An unwired script is not a watcher. This is that
# oracle landed as an arm.
#
# WHAT IS ASSERTED IS A PROPERTY, NOT A SPELLING. The arm does not look for the
# retracted sentence. It derives two sets and compares them:
#
#   C  the modules the docstrings ASSERT invoke this module
#   R  the modules that actually import it, read off the tree
#
# and requires C == R. That reddens in BOTH directions. A fabricated caller
# puts a path in C that is not in R. A caller wired up for real while the
# docstring still says nothing fires the module puts a path in R that is not
# in C - a docstring lying in the safe direction is still lying, and the next
# reader deletes the module as dead.
#
# WHY A SUBSTRING SWEEP CANNOT DO THIS JOB. The corrected docstring mentions
# `tools/precommit_gate.py` THREE times legitimately: once listing the guards
# that build a `git ls-files` corpus, once reporting that its imports are all
# stdlib, and once naming it as the site where the wiring WOULD go. It also
# describes the retracted sentence in prose so that a sweep for the lie cannot
# score a hit on the correction. All four survive here, and each one is a
# survivor row in the non-vacuity partner below.
#
# THE DISCRIMINATOR, stated so it can be argued with. A sentence is a caller
# claim only when it carries ALL THREE of a module path, a symbol this module
# actually defines, and a caller verb - after code blocks are removed. The
# three legitimate path mentions carry no own-symbol. The description of the
# retracted sentence carries an own-symbol and a verb but names the gate by
# nickname rather than by path. The proposed wiring carries the own-symbol
# only inside an indented code block, which is stripped.
#
# WHAT THIS IS BLIND TO, named rather than discovered later.
#   1. No modality analysis. A sentence is judged by its three tokens, not its
#      tense or mood. So a HISTORICAL or HYPOTHETICAL mention that puts a path
#      and an own-symbol in one sentence reads as a live claim and reddens.
#      That is deliberate: the opposite choice lets a real lie escape behind a
#      "would". It makes the discipline the earlier slice already used into a
#      rule - when retracting or proposing, name the module by nickname or
#      keep the symbol out of that sentence.
#   2. Sentence splitting is by terminal punctuation. A claim spread across
#      two sentences is not seen.
#   3. `R` is built from imports, not from call graphs. A module that reaches
#      this one through `importlib` or a subprocess is invisible.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MODULE_UNDER_TEST = "tools/corpus_statement.py"
_OWN_TEST_MODULE = "tests/test_corpus_statement.py"

_CALLER_VERB = re.compile(
    r"\b(?:invoke|invokes|invoked|invoking"
    r"|call|calls|called|calling"
    r"|fire|fires|fired|firing"
    r"|consume|consumes|consumed|consuming"
    r"|wire|wires|wired|wiring"
    r"|import|imports|imported|importing"
    r"|execute|executes|executed|executing)\b",
    re.IGNORECASE,
)

_MODULE_PATH = re.compile(
    r"\b((?:tools|tests|scripts|core|engines|ingest|headless|ops|agents|shell"
    r"|surface|data|docs)/[A-Za-z0-9_./-]*\.py)\b"
)

# "NOTHING FIRES THIS MODULE", "Nothing calls this today". A negative
# existential within a short reach of a caller verb.
_NO_CALLER_DECLARATION = re.compile(
    r"\bnothing\b[^.]{0,60}?"
    r"\b(?:fires?|calls?|invokes?|imports?|consumes?|wires?|executes?)\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _indented_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Contiguous runs of lines indented four or more columns, as (start, stop)."""
    blocks: list[tuple[int, int]] = []
    start: int | None = None
    for index, line in enumerate(lines):
        indented = bool(line.strip()) and line.startswith("    ")
        if indented and start is None:
            start = index
        elif not indented and start is not None and not line.strip():
            continue  # a blank line does not end a block
        elif not indented and start is not None:
            blocks.append((start, index))
            start = None
    if start is not None:
        blocks.append((start, len(lines)))
    return blocks


def _strip_code_blocks(docstring: str) -> str:
    """Remove indented blocks that are REAL PYTHON, keeping indented prose.

    The test is structural rather than textual: dedent the block and try to
    parse it. The proposed-wiring example parses as an import, an assignment
    and an `if`, so it goes. An `Args:` entry and the two `git ls-files`
    command lines do not parse, so they stay and remain searchable. A sweep
    that stripped every indented line would go blind to any claim written
    inside an argument description, which is planted row 8 below.
    """
    lines = docstring.splitlines()
    drop: set[int] = set()
    for start, stop in _indented_blocks(lines):
        block = textwrap.dedent("\n".join(lines[start:stop]))
        if not block.strip():
            continue
        try:
            parsed = ast.parse(block)
        except SyntaxError:
            continue
        meaningful = [
            node
            for node in parsed.body
            if not (
                isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
            )
        ]
        if meaningful:
            drop.update(range(start, stop))
    return "\n".join(line for i, line in enumerate(lines) if i not in drop)


def _own_symbols(source: str, module_stem: str) -> set[str]:
    """The names this module defines, DERIVED rather than listed.

    A hardcoded list rots the moment a function is renamed, and a renamed
    symbol would quietly drop out of the discriminator - a suffix rename
    emptying a suffix-keyed guard is a failure this tree has already paid for.
    """
    symbols = {module_stem}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
    return symbols


def _all_docstrings(source: str) -> list[tuple[str, str]]:
    """Every docstring in the module, as (where, text), cleaned of indentation."""
    tree = ast.parse(source)
    found: list[tuple[str, str]] = []
    module_doc = ast.get_docstring(tree, clean=True)
    if module_doc:
        found.append(("module", module_doc))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=True)
            if doc:
                found.append((node.name, doc))
    return found


def _caller_claims(source: str, module_stem: str) -> tuple[int, dict[str, list[str]]]:
    """Extract the modules this source's docstrings CLAIM invoke it.

    Returns the number of sentences examined - so a caller can refuse a
    vacuous zero-out-of-zero pass - and a mapping from the claimed module path
    to the sentences making the claim.
    """
    symbols = _own_symbols(source, module_stem)
    examined = 0
    claims: dict[str, list[str]] = {}
    for _where, doc in _all_docstrings(source):
        prose = _strip_code_blocks(doc)
        for sentence in _SENTENCE_SPLIT.split(" ".join(prose.split())):
            if not sentence.strip():
                continue
            examined += 1
            paths = _MODULE_PATH.findall(sentence)
            if not paths:
                continue
            if not _CALLER_VERB.search(sentence):
                continue
            if not any(re.search(rf"\b{re.escape(s)}\b", sentence) for s in symbols):
                continue
            for path in paths:
                claims.setdefault(path, []).append(sentence.strip())
    return examined, claims


def _declares_no_caller(source: str) -> bool:
    """True when some docstring states, in so many words, that nothing fires it."""
    return any(
        _NO_CALLER_DECLARATION.search(_strip_code_blocks(doc))
        for _where, doc in _all_docstrings(source)
    )


def _tracked_python_files() -> list[str]:
    """Every tracked `.py`, discovered from git rather than listed."""
    completed = subprocess.run(
        ["git", "ls-files", "-z", "*.py"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        check=True,
    )
    return sorted(n for n in completed.stdout.decode("utf-8").split("\0") if n)


def _modules_importing(target_stem: str, exclude: set[str]) -> set[str]:
    """Tracked modules that IMPORT `target_stem`, read off the working tree.

    Working tree rather than `git show`, so a plant on disk is visible to this
    oracle the way a real new caller would be.
    """
    importers: set[str] = set()
    for name in _tracked_python_files():
        if name in exclude:
            continue
        path = _REPO_ROOT / name
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):  # pragma: no cover - defect only
            continue
        if target_stem not in source:
            continue  # cheap reject before the parse
        try:
            tree = ast.parse(source)
        except SyntaxError:  # pragma: no cover - defect only
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(a.name.split(".")[-1] == target_stem for a in node.names):
                    importers.add(name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.split(".")[-1] == target_stem or any(
                    a.name == target_stem for a in node.names
                ):
                    importers.add(name)
    return importers


def test_docstring_caller_claims_resolve_against_the_tree() -> None:
    """Any caller these docstrings name must really invoke the module, and vice versa.

    THE DEFECT THIS CLOSES, MEASURED. Until 2026-10-02 three docstrings in
    `tools/corpus_statement.py` asserted, four times between them, that the
    glyph gate invoked `untracked_not_ignored`. It never did - that file
    imports `json`, `os`, `pathlib`, `re`, `subprocess`, `sys` and a local
    `py_compile`, and nothing else. The module had no caller at all. The
    correction was checked once, by hand, from a scratchpad that was thrown
    away; this arm is that check wired in so it runs.

    BOTH DIRECTIONS REDDEN. A fabricated caller is caught because the claimed
    path is not among the real importers. A real caller landed while the
    docstring still announces that nothing fires the module is caught too,
    because the importer is not among the claims - and that second failure is
    the dangerous one, since a module documented as dead gets deleted.
    """
    require_git_repository()

    source = (_REPO_ROOT / _MODULE_UNDER_TEST).read_text(encoding="utf-8")
    stem = Path(_MODULE_UNDER_TEST).stem

    examined, claims = _caller_claims(source, stem)
    # Measured 2026-10-02 at a1ee3d3: 85 sentences across the three docstrings.
    # The floor is set well under that so ordinary prose edits do not trip it,
    # and well over zero so a docstring gutted to a one-liner does.
    assert examined >= 60, (
        f"only {examined} docstring sentences were examined in "
        f"{_MODULE_UNDER_TEST}, which is too few to be its real prose - this "
        "arm would be passing zero out of zero"
    )

    symbols = _own_symbols(source, stem)
    assert len(symbols) >= 3, (
        f"the discriminator resolved only {sorted(symbols)} as symbols of this "
        "module, so the own-symbol half of the test is nearly vacuous"
    )

    real = _modules_importing(stem, exclude={_MODULE_UNDER_TEST, _OWN_TEST_MODULE})
    # A module naming its own path is not claiming a caller, and `real` already
    # excludes it. Measured 2026-10-02 while deciding whether to generalise this
    # arm over `tools/`: two of the thirteen tracked modules there mention their
    # own path in a sentence carrying an own-symbol and a caller verb, so a
    # sweep without this line reds on them the moment it is pointed anywhere
    # else. `tools/corpus_statement.py` happens not to, today.
    claimed = set(claims) - {_MODULE_UNDER_TEST}

    fabricated = sorted(claimed - real)
    unannounced = sorted(real - claimed)

    assert not fabricated, (
        f"these docstrings in {_MODULE_UNDER_TEST} claim a caller that does "
        f"not exist. Nothing in {fabricated} imports `{stem}`. Either wire the "
        "call up or correct the prose; if the mention is historical or "
        "hypothetical, keep the module path and the symbol name out of the "
        "same sentence, which is how the surviving mentions are written. "
        f"Offending sentences: {({p: claims[p] for p in fabricated})!r}"
    )
    assert not unannounced, (
        f"{sorted(real)} really do import `{stem}`, but the docstrings of "
        f"{_MODULE_UNDER_TEST} never name them as callers. A docstring that "
        "understates its wiring is still wrong, and the next reader deletes "
        f"the module as dead code. Unannounced: {unannounced}"
    )

    if not real:
        assert _declares_no_caller(source), (
            f"{_MODULE_UNDER_TEST} has no caller anywhere in the tree and its "
            "docstrings no longer say so. Silence here is how the module gets "
            "read as wired. State it plainly, as the 2026-10-02 correction did"
        )
    else:
        assert not _declares_no_caller(source), (
            f"{sorted(real)} import `{stem}`, yet a docstring still declares "
            "that nothing fires this module"
        )


def test_the_caller_claim_detector_actually_fires() -> None:
    """NON-VACUITY. The oracle must catch planted lies and spare real neighbours.

    Without this arm `fabricated == []` is satisfied just as well by a
    discriminator that matches nothing, which is the trap half this tree's
    arms have historically fallen into. The other half is a sweep that scores
    perfectly by flagging its own subjects, so the survivors matter as much as
    the plants - every survivor row is a REAL sentence from the corrected
    docstring, including the one that DESCRIBES the retracted claim.

    Sources are built here rather than written to disk, so nothing tracked is
    mutated even briefly. No `chr()` escape is needed for the planted lie: the
    retracted paragraph was byte-inspected at 473 bytes with zero bytes above
    0x7F and no CR, so planting it verbatim cannot make this module violate
    the ASCII arm above.
    """
    head = '"""Doc.\n\n'
    tail = '"""\n\n\ndef untracked_not_ignored(root):\n    return []\n'

    planted = {
        "the retracted sentence, verbatim": (
            "NOTHING IN THIS MODULE RAISES TO ITS CALLER. `untracked_not_ignored` is\n"
            "invoked from `tools/precommit_gate.py`, which runs from a git hook, so\n"
            "any exception escaping here becomes a NON-ZERO HOOK EXIT.\n"
        ),
        "present tense, calls": (
            "`tools/precommit_gate.py` calls `untracked_not_ignored` on every run.\n"
        ),
        "passive, is called from": (
            "`untracked_not_ignored` is called from `scripts/install_hooks.py`.\n"
        ),
        "fires rather than calls": (
            "The sweep in `tests/test_no_sibling_names.py` fires "
            "`untracked_not_ignored`.\n"
        ),
        "named by the module stem": (
            "`ops/supervisor.py` imports `corpus_statement` at startup.\n"
        ),
        "consumes": (
            "`headless/runner.py` consumes `untracked_not_ignored` once a pass.\n"
        ),
        "wrapped across source lines": (
            "The glyph gate at\n`tools/precommit_gate.py`\ninvokes\n"
            "`untracked_not_ignored`.\n"
        ),
        "claim sitting inside an Args entry": (
            "Args:\n"
            "    root: the directory. `tools/precommit_gate.py` invokes\n"
            "    `untracked_not_ignored` with the repo root here.\n"
        ),
    }
    for label, body in planted.items():
        _examined, claims = _caller_claims(head + body + tail, "corpus_statement")
        assert claims, (
            f"{label}: the detector missed a planted caller claim in {body!r}"
        )

    survivors = {
        "guards listed by the corpus they build": (
            "Three guards in this tree build their corpus from `git ls-files` - the\n"
            "glyph gate at `tools/precommit_gate.py`, the sibling-name sweep at\n"
            "`tests/test_no_sibling_names.py`, and the docs pointer guard at\n"
            "`tests/test_docs_consistency.py`.\n"
        ),
        "the measurement that proves there is no caller": (
            "Measured: `tools/precommit_gate.py` imports `json`, `os`, `pathlib`,\n"
            "`re`, `subprocess`, `sys` and - locally, inside a function -\n"
            "`py_compile`. Stdlib, all of it.\n"
        ),
        "the retraction, which names the gate by nickname": (
            "Until 2026-10-02 this docstring named the glyph gate as the thing that\n"
            "calls `untracked_not_ignored`. That was FALSE and had been false since\n"
            "the module landed.\n"
        ),
        "the proposed wiring, symbol only inside a code block": (
            "The natural site is the glyph gate's corpus construction in\n"
            "`tools/precommit_gate.py`: after it builds its `git ls-files` corpus,\n"
            "call\n"
            "\n"
            "    from tools.corpus_statement import untracked_not_ignored\n"
            "    unscanned = untracked_not_ignored(repo_root)\n"
            "    if unscanned:\n"
            '        print("NOT SCANNED: " + ", ".join(unscanned))\n'
            "\n"
            "and STILL EXIT 0, per the ruling below.\n"
        ),
        "the write-list reason the wiring is not landed": (
            "That change is not made here because `tools/precommit_gate.py` is\n"
            "outside this change's write-list, and because a gate's PRESENCE is\n"
            "never proof it runs.\n"
        ),
        "the own-test-module mention, no caller verb": (
            "Across every tracked file the only thing that names `corpus_statement`\n"
            "at all is `tests/test_corpus_statement.py`, its own test module.\n"
        ),
    }
    for label, body in survivors.items():
        _examined, claims = _caller_claims(head + body + tail, "corpus_statement")
        assert not claims, (
            f"{label}: a legitimate neighbour was read as a caller claim, which "
            "is how a sweep scores perfectly by deleting its own subjects: "
            f"{claims}"
        )

    # A SELF-mention is not a caller claim. The extractor reports it, and the
    # arm above subtracts it; both halves are checked here because only the
    # pair is the behaviour. Measured in `tools/` before deciding against
    # generalising: two of thirteen modules carry exactly this shape.
    _examined, self_claims = _caller_claims(
        head
        + "The helper in `tools/corpus_statement.py` invokes "
        + "`untracked_not_ignored` on itself.\n"
        + tail,
        "corpus_statement",
    )
    assert set(self_claims) == {_MODULE_UNDER_TEST}, self_claims
    assert set(self_claims) - {_MODULE_UNDER_TEST} == set()

    # The no-caller declaration half, both polarities.
    assert _declares_no_caller(head + "NOTHING FIRES THIS MODULE.\n" + tail)
    assert _declares_no_caller(head + "Nothing calls this today.\n" + tail)
    assert not _declares_no_caller(head + "This module is a helper.\n" + tail)

    # The code-block stripper must remove python and keep prose.
    stripped = _strip_code_blocks(
        "Prose.\n\n    x = untracked_not_ignored(root)\n\nMore prose.\n"
    )
    assert "untracked_not_ignored" not in stripped, stripped
    kept = _strip_code_blocks(
        "Prose.\n\n    git ls-files --others --exclude-standard\n\nMore prose.\n"
    )
    assert "git ls-files" in kept, kept
