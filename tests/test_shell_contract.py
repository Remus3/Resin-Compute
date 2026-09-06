"""Guards on the Electron shell that only the Python suite can enforce.

THE SHELL IS GRADED BY `node --test`, and that suite is the right home for
anything about menus, geometry or state parsing. Three things it cannot check
live here instead:

1. **The port crosses a language boundary.** `core/ports.py` owns the number and
   `shell/lib/endpoint.js` restates it, because a JavaScript module cannot import
   a Python one. Duplication across a boundary is legitimate; UNGUARDED
   duplication is not, so this file reads the JavaScript as text and asserts the
   two agree. Without it the shell would keep loading a stale port and the
   failure would present as a blank window rather than as a wrong constant.

2. **The 7-bit ASCII rule.** `shell/` is authored text like everything else, and
   the git hooks sweep staged files rather than the tree. A regenerated icon or a
   pasted smart quote should fail a test, not only a commit.

3. **No sibling port literal.** `tests/test_ports.py` parses Python only, so the
   shell would be a blind spot in an otherwise total sweep.

All three grade a FILE LIST, so the list is the real input and gets the same
scrutiny as the assertions. It is derived from `git ls-files`, never from a
walk of `shell/` - see `_tracked_under_shell` for why the distinction is not
pedantry. `shell/` is where contributors run `npm install` and `electron-builder`,
and git stores no empty directories and knows nothing of ignored ones.
"""
from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

from core import ports
from tests.conftest import skip_module_without_git

REPO_ROOT = Path(__file__).resolve().parent.parent
SHELL_DIR = REPO_ROOT / "shell"

# MODULE-LEVEL, and it has to be. Every other git-dependent guard in this
# directory calls `require_git_repository()` at run time, which is narrower and
# keeps unrelated tests in the same module alive. That does not work HERE: the
# sweep below is a `@pytest.mark.parametrize` argument, so git is invoked while
# this module is being IMPORTED. A run-time skip is too late - the exception
# escapes collection and pytest reports a collection ERROR, which aborts the
# WHOLE RUN rather than skipping one file.
#
# Measured 2026-09-06 against a 147-file `git archive` extract: that is exactly
# what happened, and NOT ONE TEST IN THE SUITE RAN - exit 2, for the public that
# receives this repository as a Download-ZIP, an sdist or a vendored copy.
skip_module_without_git()


# ---------------------------------------------------------------------------
# What gets swept, and why it is asked of git rather than of the disk
# ---------------------------------------------------------------------------


class ShellSourceDiscoveryError(RuntimeError):
    """git could not enumerate shell/, so every sweep below would be vacuous.

    Raised rather than returning an empty list. A guard that quietly stops
    finding files passes forever and reports nothing, which is worse than a
    guard that was never written - it also carries a green tick.
    """


def _git(*args: str, stdin: str | None = None, ok: tuple[int, ...] = (0,)) -> str:
    """Run git from `REPO_ROOT` and return stdout, or raise a named error.

    `cwd` is the repo root derived from `__file__`, never the process working
    directory: pytest can be invoked from anywhere, and a relative pathspec
    resolved against some other directory would silently sweep the wrong tree.
    """
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            input=stdin,
            capture_output=True,
            text=True,
        )
    except OSError as exc:  # git absent from PATH, or not executable
        raise ShellSourceDiscoveryError(f"could not run `git {' '.join(args)}`: {exc}") from exc
    if done.returncode not in ok:
        raise ShellSourceDiscoveryError(
            f"`git {' '.join(args)}` exited {done.returncode}: {done.stderr.strip()}"
        )
    return done.stdout


@lru_cache(maxsize=1)
def _tracked_under_shell() -> tuple[str, ...]:
    """Every path git TRACKS under shell/, as repo-relative posix strings.

    Asked of the INDEX, not of the filesystem, and the difference is the whole
    point. A disk walk sweeps whatever happens to be lying in the directory,
    and `shell/` is precisely a directory contributors run build tooling in:
    `npm install` writes `node_modules/`, and `electron-builder` - which this
    `shell/package.json` declares the devDependency for - writes `dist/`.
    Neither is in anybody's clone. Grading them is grading vendored third-party
    code against this project's house style.

    An ad-hoc denylist is not the fix, it is the bug in a friendlier costume.
    It lists the ignore rules whoever wrote it happened to remember, and the
    rules here live in TWO files - the root `.gitignore` and `shell/.gitignore`
    - so the remembering is guaranteed to be partial. The version this replaced
    remembered `node_modules/` and missed `dist/`, `build/`, `tmp/`,
    `_scratch/`, `.vscode/` and `.mypy_cache/`, every one of which the root
    file matches at any depth.

    `-z` because `core.quotePath` escapes non-ASCII and space-bearing paths in
    the default output format, turning them into paths that do not exist.
    """
    out = tuple(p for p in _git("ls-files", "-z", "--", "shell").split("\0") if p)
    if not out:
        raise ShellSourceDiscoveryError(
            "`git ls-files -- shell` reported nothing; every shell/ sweep below would be vacuous"
        )
    return out


#: Suffixes worth reading. `.gitignore` is carried by name because it has none.
_SWEPT_SUFFIXES = {".js", ".json", ".md"}


def _shell_sources() -> list[Path]:
    """The tracked, readable source files under shell/, as absolute paths."""
    out: list[Path] = []
    for rel in _tracked_under_shell():
        path = REPO_ROOT / rel
        if path.suffix not in _SWEPT_SUFFIXES and path.name != ".gitignore":
            continue
        if not path.is_file():
            # In the index but not on disk: staged-then-deleted, or a sparse
            # checkout. An ordinary transient state with nothing to do with
            # this guard's subject, and it can hide no offender, because a file
            # that is not on disk carries no content to inspect. Skipped rather
            # than raised on, matching the precedent in tests/test_ports.py.
            continue
        out.append(path)
    if not out:
        raise ShellSourceDiscoveryError(
            f"none of the {len(_tracked_under_shell())} tracked paths under shell/ was readable source"
        )
    return out


def _shell_source_rel_paths() -> list[str]:
    """The swept set as repo-relative posix strings, ready to hand back to git."""
    return [p.relative_to(REPO_ROOT).as_posix() for p in _shell_sources()]


def _paths_git_ignores(paths: list[str]) -> list[str]:
    """Which of `paths` an ignore rule matches, asked of git itself.

    A DIFFERENT oracle from the `git ls-files` that produced the list, which is
    the only reason asserting on it is worth anything.

    `--no-index` is load-bearing. Without it git short-circuits on trackedness
    and answers "not ignored" for every tracked path by construction - the arm
    would then agree with `ls-files` for free and prove nothing at all. With
    it, the exclude rules alone are consulted, so the two oracles can disagree.

    `-z` sets the INPUT separator as well as the output one. Newline-joined
    input is read as a SINGLE path with embedded newlines - measured here, and
    the same trap `tests/test_line_endings.py` records against
    `git check-attr --stdin`.
    """
    if not paths:
        return []
    # Exit 1 is "none of them is ignored" - the answer this wants, not a
    # failure. Anything outside {0, 1} is a real error and `_git` raises.
    out = _git("check-ignore", "--stdin", "-z", "--no-index", stdin="\0".join(paths), ok=(0, 1))
    return [p for p in out.split("\0") if p]


#: Anchors pinned by REPO-RELATIVE PATH rather than by basename.
#:
#: `len(sources) >= 8` plus a set of bare filenames was the whole previous
#: floor, and a floor cannot notice OVER-collection: it stayed green while the
#: sweep was also grading two files out of an ignored `shell/dist/`. Basenames
#: make that worse, because a vendored tree supplies them in bulk - one
#: `npm install` puts hundreds of `package.json` and `index.js` files under
#: `shell/`, so a basename anchor is satisfiable by content nobody clones. A
#: repo-relative path is not: only the real file has it.
SHELL_ANCHORS = frozenset(
    {
        "shell/main.js",
        "shell/preload.js",
        "shell/package.json",
        "shell/lib/endpoint.js",
        "shell/lib/window.js",
        "shell/lib/tray.js",
        "shell/test/lib.test.js",
    }
)

#: One canary per ignore FILE. The rules live in two of them, and remembering
#: exactly one is the failure mode this whole change is about.
IGNORED_CANARIES = (
    "shell/node_modules/electron/dist/index.js",  # shell/.gitignore
    "shell/dist/win-unpacked/resources/app/bundle.js",  # the root .gitignore
)


def test_the_shell_directory_exists_and_has_sources():
    """Non-vacuity. A sweep that silently found nothing would pass forever.

    The floor arms are kept; the path anchors are what makes them mean
    something. A count and a set of basenames can both be satisfied by a
    vendored tree, so on their own they detect under-collection only.
    """
    sources = _shell_sources()
    assert len(sources) >= 8, f"only found {len(sources)} shell sources"
    names = {p.name for p in sources}
    assert {"main.js", "preload.js", "package.json", "tray.js"} <= names

    rel = set(_shell_source_rel_paths())
    missing = sorted(SHELL_ANCHORS - rel)
    assert not missing, f"the shell sweep no longer reaches {missing}"


def test_the_javascript_dashboard_port_matches_the_python_registry():
    """The cross-boundary pin. This is the test this file exists for."""
    text = (SHELL_DIR / "lib" / "endpoint.js").read_text(encoding="utf-8")
    match = re.search(r"const\s+DEFAULT_PORT\s*=\s*(\d+)\s*;", text)
    assert match, "shell/lib/endpoint.js has no DEFAULT_PORT to pin"
    assert int(match.group(1)) == ports.DASHBOARD


def test_the_javascript_default_host_is_loopback():
    text = (SHELL_DIR / "lib" / "endpoint.js").read_text(encoding="utf-8")
    match = re.search(r'const\s+DEFAULT_HOST\s*=\s*"([^"]+)"\s*;', text)
    assert match
    assert match.group(1) == "127.0.0.1"


@pytest.mark.parametrize("path", _shell_sources(), ids=lambda p: p.name)
def test_every_shell_source_is_seven_bit_ascii(path: Path):
    """No em-dash, no en-dash, no smart quote, anywhere under shell/.

    The tray icon is base64 precisely so this can hold with a raster image in the
    tree, so a regenerated icon that left the alphabet fails here.
    """
    raw = path.read_bytes()
    offenders = [(i, byte) for i, byte in enumerate(raw) if byte > 0x7E]
    assert not offenders, f"{path.name} carries non-ASCII bytes at {offenders[:5]}"


def test_no_shell_source_carries_a_sibling_port_literal():
    """`tests/test_ports.py` parses Python only, so shell/ would be a blind spot."""
    foreign: set[int] = set()
    for name, block in ports.BLOCKS.items():
        if name == "rsc":
            continue
        foreign.update(block)

    offenders: list[str] = []
    for path in _shell_sources():
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\b(\d{4,5})\b", text):
            if int(match.group(1)) in foreign:
                line = text[: match.start()].count("\n") + 1
                offenders.append(f"{path.name}:{line} carries {match.group(1)}")
    assert not offenders, "foreign port literals under shell/: " + "; ".join(offenders)


def test_the_tray_icon_payload_carries_no_adjacent_solidus_pair():
    """Two of them open a line comment to any text scanner, this one included."""
    text = (SHELL_DIR / "lib" / "tray.js").read_text(encoding="utf-8")
    chunks = re.findall(r'"([A-Za-z0-9+/=]{20,})"', text)
    assert chunks, "no base64 chunks found in tray.js"
    payload = "".join(chunks)
    assert "//" not in payload


def test_the_security_flags_are_present_in_the_window_module():
    """A defence in depth over the node suite, which pins them by value.

    These four are wrong by OMISSION, and an omitted flag has no line of code for
    a reviewer to look at. Asserting the text is present catches a deletion that
    a truthiness test would not.
    """
    text = (SHELL_DIR / "lib" / "window.js").read_text(encoding="utf-8")
    for flag in ("nodeIntegration: false", "contextIsolation: true", "sandbox: true", "webSecurity: true"):
        assert flag in text, f"shell/lib/window.js no longer sets {flag}"


def test_the_main_process_makes_no_decision_the_libs_should_own():
    """ADR-005's rule: main.js is wiring only, because no test can load it.

    A crude check, deliberately. It looks for the two shapes that would mean a
    real decision migrated back into the untestable file - a hardcoded port, and
    a security flag set inline rather than through window.js.
    """
    text = (SHELL_DIR / "main.js").read_text(encoding="utf-8")
    assert not re.search(r"\b8\d{3}\b", text), "main.js carries a port literal; endpoint.js owns that"
    assert "nodeIntegration" not in text, "main.js sets a security flag; window.js owns those"


# ---------------------------------------------------------------------------
# The sweep is graded by a second oracle
# ---------------------------------------------------------------------------


def test_no_swept_shell_source_is_a_path_git_ignores():
    """The permanent arm. It holds without anything being on disk to catch.

    Every assertion above grades whatever `_shell_sources()` hands it, so the
    file list is the guard's real input and nothing was checking it. This asks
    a second, independent git command whether any swept path is one an ignore
    rule matches. It should be impossible by construction, since the list came
    from the index - which is exactly what makes it a useful cross-check: if it
    ever fires, the derivation has regressed to a disk walk.
    """
    swept = _shell_source_rel_paths()
    ignored = _paths_git_ignores(swept)
    assert not ignored, "the shell sweep is grading gitignored content: " + "; ".join(ignored)


def test_the_ignored_path_detector_actually_fires():
    """Non-vacuity for the arm above, which would otherwise pass by finding nothing.

    Feeds the real list plus one canary per ignore file - the exact shape a
    disk walk produces - and demands the answer back be exactly the canaries.
    `== ` rather than a membership check, so the arm fails if it also
    misfires on a legitimate neighbour: a detector that flags everything is as
    useless as one that flags nothing, and only one of those is obvious.
    """
    swept = _shell_source_rel_paths()
    for canary in IGNORED_CANARIES:
        assert canary not in swept, f"{canary} is meant to be unreachable by the sweep"

    flagged = _paths_git_ignores(swept + list(IGNORED_CANARIES))
    assert flagged == list(IGNORED_CANARIES), f"the ignored-path detector reported {flagged}"


def test_the_shell_source_list_comes_from_the_index_not_the_disk():
    """The regression pin on the root cause itself.

    Guarded by identity rather than by count: the swept set must be a subset of
    what `git ls-files` reports, which no filesystem walk can promise.
    """
    tracked = set(_tracked_under_shell())
    assert tracked, "git reported no tracked paths under shell/"

    stray = sorted(set(_shell_source_rel_paths()) - tracked)
    assert not stray, f"swept paths that git does not track: {stray}"
