"""The working tree must match the line endings `.gitattributes` declares.

WHY A BYTE CHECK ON DISK, AND WHY A DIFF CHECK WOULD BE VACUOUS.

`.gitattributes` sets `* text=auto eol=lf` plus explicit `eol=lf` for every
source suffix, and its own header says that forcing this "pins the bytes in the
repo AND in the working tree, which overrides autocrlf so neither can recur".

The first half of that is enforced by git itself: content is normalised to LF on
the way into the index, so `git diff` on a CRLF working file shows NOTHING but a
warning. The second half was enforced by nothing at all, and drifted - measured
2026-09-06, 16 of 72 tracked `.py` files carried CRLF on disk while every diff
in the repository looked clean. Editors and tooling that write CRLF on save
produce exactly this, silently, forever.

So the only meaningful check is the one below: read the BYTES off disk. A test
that compared the index to the working tree would agree with itself and pass
while the drift accumulated, which is precisely what happened.

Sibling-C paid for the CRLF class of bug twice, including 21 tracked `.py`
files with doubled CR endings, and `.gitattributes` cites that as the reason the
policy exists. The `.githooks/` shims are the sharper case: they are `#!/bin/sh`
scripts, and a CRLF shebang makes the kernel look for an interpreter named
"/bin/sh\r", so the whole commit-time gate goes silently absent.

NOT A CI TEST IN PRACTICE. A fresh checkout on the Linux runner honours
`eol=lf`, so this passes there by construction. Its value is local, on the
Windows machines where the drift is actually produced.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent

CRLF = b"\r\n"


def _git(*args: str) -> str:
    # Guarded HERE rather than at module level: the two arms below that read
    # bytes off disk - the .githooks/ shims and the CRLF detector itself - need
    # no repository and must keep running in a Download-ZIP copy.
    require_git_repository()
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _tracked_files() -> list[str]:
    return [line for line in _git("ls-files").splitlines() if line]


def _files_declared_lf() -> list[str]:
    """Every tracked path whose `.gitattributes` rule resolves to `eol=lf`.

    Asked of git rather than reimplemented, so the answer cannot drift from the
    rules actually in force. `check-attr -z` is used because a filename may
    contain a colon, which the default output format also uses as a separator.
    """
    tracked = _tracked_files()
    if not tracked:
        return []

    completed = subprocess.run(
        ["git", "check-attr", "--stdin", "-z", "eol"],
        cwd=REPO_ROOT,
        # -z changes the INPUT separator as well as the output one. Feeding
        # newline-separated paths here makes git read the whole list as a
        # single path with embedded newlines, and the sweep silently collapses
        # to one bogus entry - which still passes a naive assertion.
        input="\0".join(tracked),
        capture_output=True,
        text=True,
        check=True,
    )
    # -z emits a flat NUL-separated stream of (path, attribute, value) triples.
    fields = completed.stdout.split("\0")
    return [
        fields[i]
        for i in range(0, len(fields) - 2, 3)
        if fields[i + 1] == "eol" and fields[i + 2] == "lf"
    ]


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_no_file_declared_eol_lf_carries_crlf_in_the_working_tree():
    offenders = []
    for name in _files_declared_lf():
        path = REPO_ROOT / name
        if not path.is_file():
            continue  # A deleted-but-staged path is not this test's problem.
        count = path.read_bytes().count(CRLF)
        if count:
            offenders.append(f"{name} ({count} CRLF)")

    assert not offenders, (
        "these files declare eol=lf but carry CRLF on disk; the index hides "
        "this so no diff will show it: " + ", ".join(sorted(offenders))
    )


def test_the_githooks_shims_are_lf_because_a_crlf_shebang_breaks_them():
    """Called out separately because the failure here is a SILENT missing gate.

    A CRLF shebang makes the kernel look for an interpreter literally named
    "/bin/sh\\r". The hook then fails with an unreadable error or is skipped,
    and a gate that is absent without saying so is the whole thing this
    scaffold exists to prevent.
    """
    for shim in sorted((REPO_ROOT / ".githooks").iterdir()):
        if shim.is_file():
            assert CRLF not in shim.read_bytes(), f".githooks/{shim.name} has CRLF"


# ---------------------------------------------------------------------------
# Non-vacuity - a sweep that stopped finding files would pass forever
# ---------------------------------------------------------------------------


def test_the_sweep_selects_a_realistic_number_of_files():
    declared = _files_declared_lf()
    assert len(declared) >= 50, f"only {len(declared)} files resolved to eol=lf"
    assert "core/types.py" in declared
    assert "CLAUDE.md" in declared


def test_the_sweep_excludes_files_declared_binary():
    """`.gitattributes` marks images and archives binary; they must not appear."""
    declared = set(_files_declared_lf())
    assert not [name for name in declared if name.endswith((".png", ".jpg", ".ico", ".zip"))]


def test_a_crlf_byte_would_actually_be_detected(tmp_path):
    """Aimed at the detection itself, not at the file list."""
    clean = tmp_path / "clean.txt"
    dirty = tmp_path / "dirty.txt"
    clean.write_bytes(b"one\ntwo\n")
    dirty.write_bytes(b"one\r\ntwo\n")
    assert clean.read_bytes().count(CRLF) == 0
    assert dirty.read_bytes().count(CRLF) == 1


@pytest.mark.parametrize("suffix", [".py", ".md", ".json", ".yml", ".toml", ".ini"])
def test_every_source_suffix_the_tree_uses_is_covered_by_the_sweep(suffix: str):
    """A suffix that stopped resolving to eol=lf would silently leave the guard."""
    declared = _files_declared_lf()
    tracked_with_suffix = [name for name in _tracked_files() if name.endswith(suffix)]
    if not tracked_with_suffix:
        pytest.skip(f"no tracked {suffix} files")
    assert any(name.endswith(suffix) for name in declared), f"{suffix} is not covered"
