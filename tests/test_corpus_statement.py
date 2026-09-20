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

import logging
import subprocess
from pathlib import Path

import pytest

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
