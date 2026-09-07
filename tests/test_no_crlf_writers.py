"""No runtime writer may call `Path.write_text` without pinning `newline=`.

THE DEFECT THIS GUARDS, measured in this tree 2026-09-07.

`Path.write_text(text, encoding=...)` opens the file with `newline=None`, and
`newline=None` is NOT "leave the caller's bytes alone" - it is the translation
mode. Every `\\n` in `text` becomes `os.linesep` on the way out, which is
`\\r\\n` on Windows. `core/atomic_io.py` - the module CLAUDE.md names as the ONLY
sanctioned state-write path - carried exactly this and was fixed in e1b20e6:
`atomic_write_text(p, "a\\nb\\n")` produced `b'a\\r\\nb\\r\\n'`, and a caller who
supplied CRLF got back CR-CR-LF, the CR kept and the LF expanded underneath it.

The fix is `newline="\\n"`, which disables the translation layer outright. Not
`os.linesep`, and not rewriting the caller's own bytes.

It is not a cosmetic bug. `.gitattributes` pins `* text=auto eol=lf`, so a
translated write into a TRACKED path reddens `tests/test_line_endings.py` with
nothing in `git diff` to explain it - git normalises on the way into the index,
so the diff looks clean while the working tree drifts. And an artefact written
outside the repo just silently carries the wrong bytes: measured this run,
`captured_url.json` under the first-run capture root held 5 CRLF pairs and 0
lone LF, written by `tools/wish_authkey.py`.

SCOPE, AND WHY IT STOPS WHERE IT DOES.

The corpus is every tracked `.py` OUTSIDE `tests/`. Two deliberate exclusions:

1. `tests/` is out. Eleven test modules call `write_text` today, almost all of
   them planting deliberately corrupt or truncated fixtures in `tmp_path` where
   the line endings are irrelevant to what is being asserted. Sweeping them in
   is a much larger change than the runtime fix this guard accompanies, and it
   would buy a rule that fires on fixtures rather than on artefacts anyone
   reads. If a test ever needs byte-exact output it should assert on
   `read_bytes()` anyway, which this guard cannot help with.
2. Non-Python and untracked files are out by construction, below.

THE CORPUS COMES FROM `git ls-files`, NEVER FROM `rglob`. There are live linked
worktrees under `.claude/worktrees/` in this tree right now. `rglob` descends
into a nested checkout and would sweep another agent's in-progress bytes;
`git ls-files` does not, because git does not descend into a nested repository.
That is the same structural immunity `tests/test_guard_worktree_exclusion.py`
exists to give the guards that must use a filesystem walk.

WHY `ast` AND NOT A REGEX. Two of the seven sites this guard was written
alongside - `tools/capture_supervisor.py` and `tools/first_run_capture.py` -
already pass `newline="\\n"`, but on the CONTINUATION line of a wrapped call. A
line-oriented `grep -v newline=` reports both as offenders, and a line-oriented
guard would demand a fix to code that is already correct. `ast` sees the call,
not the line, so a wrapped argument list is read the same as a flat one.

HOW THIS FILE AVOIDS TRIPPING ITS OWN SWEEP, stated plainly rather than hidden.
A detector whose own pattern matches itself is a known failure in this tree. The
answer here is NOT a self-exemption and NOT an obfuscated literal: this module
genuinely never calls `.write_text`. The positive-control fixture below is
planted with `write_bytes`, and the offending source it plants lives in a string
constant. `ast` only ever flags a Call node, so a literal inside a string is
invisible to it. There is therefore nothing to exempt, and `tests/` being out of
scope is not what saves this file - it would pass even if it were swept.

NON-VACUITY. `test_checker_fires_on_a_planted_offender` proves the detector
actually detects, and `test_checker_spares_a_compliant_writer` proves it has not
been armed by flagging everything. Without both, a clean sweep and an unarmed
sweep look identical.
"""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The keyword that must be present on every `.write_text(...)` call.
REQUIRED_KEYWORD = "newline"

#: Path prefixes excluded from the sweep. See the SCOPE note in the docstring.
EXCLUDED_PREFIXES = ("tests/",)

#: The floor the sweep must clear before its offender list means anything.
#: Zero out of zero reads as a pass, so the count is asserted FIRST. Measured
#: 2026-09-07: 58 tracked non-test `.py` files. The floor is set below that so
#: ordinary growth and pruning do not redden it, but a corpus that collapsed to
#: a handful - a broken `git ls-files`, a wrong root, a bad filter - cannot slip
#: through as a green run.
MINIMUM_CHECKED = 30


def _tracked_python_files() -> list[str]:
    """Every tracked `.py` path in scope, as repo-relative POSIX strings.

    `git ls-files` rather than `rglob`, for the nested-checkout reason in the
    module docstring.
    """
    require_git_repository()
    completed = subprocess.run(
        ["git", "ls-files", "--", "*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        line
        for line in completed.stdout.splitlines()
        if line and not line.startswith(EXCLUDED_PREFIXES)
    ]


def offending_lines(source: str) -> list[int]:
    """Line numbers of `.write_text(...)` calls in `source` with no `newline=`.

    A source that will not parse raises `SyntaxError` to the caller rather than
    being silently skipped: a file the checker cannot read is an unknown, not a
    pass.
    """
    tree = ast.parse(source)
    found: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "write_text":
            continue
        names = {kw.arg for kw in node.keywords}
        # `**kwargs` shows up as an arg of None. Treat it as satisfying the
        # rule: the checker cannot see inside it, and refusing it would be a
        # claim it has no evidence for.
        if REQUIRED_KEYWORD in names or None in names:
            continue
        found.append(node.lineno)
    return found


def scan(root: Path, relative_paths: list[str]) -> tuple[int, list[str]]:
    """Return `(files_checked, offenders)` for `relative_paths` under `root`.

    Offenders are formatted `path:lineno`, matching what `git grep -n` prints,
    so a failure message can be pasted straight into an editor.
    """
    checked = 0
    offenders: list[str] = []
    for relative in relative_paths:
        source = (root / relative).read_text(encoding="utf-8")
        checked += 1
        for lineno in offending_lines(source):
            offenders.append(f"{relative}:{lineno}")
    return checked, offenders


# ---------------------------------------------------------------------------
# The sweep
# ---------------------------------------------------------------------------


def test_no_tracked_runtime_writer_omits_newline() -> None:
    """No tracked non-test `.py` calls `write_text` without pinning `newline=`."""
    paths = _tracked_python_files()
    checked, offenders = scan(REPO_ROOT, paths)

    # COUNT FIRST. An empty offender list is only evidence if something was
    # actually opened.
    assert checked >= MINIMUM_CHECKED, (
        f"sweep only opened {checked} tracked non-test .py files, below the "
        f"floor of {MINIMUM_CHECKED} - the corpus is wrong, not clean"
    )
    assert offenders == [], (
        "Path.write_text without newline='\\n' translates every LF to os.linesep "
        "on Windows. Pin newline='\\n' at each site below:\n  "
        + "\n  ".join(offenders)
    )


# ---------------------------------------------------------------------------
# Non-vacuity: the detector must fire, and must not fire on everything
# ---------------------------------------------------------------------------


_OFFENDING_SOURCE = (
    "from pathlib import Path\n"
    "\n"
    "def save(p: Path, text: str) -> None:\n"
    "    tmp = p.with_suffix('.tmp')\n"
    "    tmp.write_text(text, encoding='utf-8')\n"
    "    tmp.replace(p)\n"
)

_COMPLIANT_SOURCE = (
    "from pathlib import Path\n"
    "\n"
    "def save(p: Path, text: str) -> None:\n"
    "    tmp = p.with_suffix('.tmp')\n"
    "    tmp.write_text(text, encoding='utf-8', newline='\\n')\n"
    "    tmp.replace(p)\n"
)

# The shape that defeats a line-oriented grep: the keyword sits on the
# continuation line. `tools/capture_supervisor.py` and
# `tools/first_run_capture.py` are both written exactly like this.
_COMPLIANT_WRAPPED_SOURCE = (
    "from pathlib import Path\n"
    "\n"
    "def save(p: Path, text: str) -> None:\n"
    "    tmp = p.with_suffix('.tmp')\n"
    "    tmp.write_text(text,\n"
    "                   encoding='utf-8', newline='\\n')\n"
    "    tmp.replace(p)\n"
)


def test_checker_fires_on_a_planted_offender(tmp_path: Path) -> None:
    """POSITIVE CONTROL. Without this, clean and unarmed are indistinguishable.

    The fixture is planted with `write_bytes`, not `write_text` - see the
    self-sweep note in the module docstring.
    """
    planted = tmp_path / "offender.py"
    planted.write_bytes(_OFFENDING_SOURCE.encode("ascii"))

    checked, offenders = scan(tmp_path, ["offender.py"])

    assert checked == 1
    assert offenders == ["offender.py:5"], offenders


def test_checker_spares_a_compliant_writer(tmp_path: Path) -> None:
    """The legitimate neighbour survives. A detector that flags both is useless."""
    compliant = tmp_path / "compliant.py"
    compliant.write_bytes(_COMPLIANT_SOURCE.encode("ascii"))

    checked, offenders = scan(tmp_path, ["compliant.py"])

    assert checked == 1
    assert offenders == []


def test_checker_reads_calls_not_lines(tmp_path: Path) -> None:
    """A wrapped call whose `newline=` is on the continuation line is compliant.

    This is the case a `grep -v newline=` sweep gets wrong, and it is why the
    checker parses rather than scans.
    """
    wrapped = tmp_path / "wrapped.py"
    wrapped.write_bytes(_COMPLIANT_WRAPPED_SOURCE.encode("ascii"))

    checked, offenders = scan(tmp_path, ["wrapped.py"])

    assert checked == 1
    assert offenders == []


# ---------------------------------------------------------------------------
# Behavioural: the fixed writers put the caller's bytes on disk
# ---------------------------------------------------------------------------
#
# The sweep above is static. These two arms run the real writers and read the
# result with `read_bytes()`, never `read_text()` - `read_text` translates CRLF
# back to LF on the way in and makes a broken writer look correct, which is the
# reason this whole class of defect survived as long as it did.


def test_bootstrap_fallback_writer_emits_lf(tmp_path: Path) -> None:
    """`scripts/bootstrap_data.py`'s local fallback must not translate.

    The live path: its default output sits under `data/`, which `.gitignore`
    does not exclude, so a translated write reaches a trackable file.
    """
    from scripts.bootstrap_data import _fallback_atomic_write

    target = tmp_path / "account_snapshot.json"
    _fallback_atomic_write(target, '{\n  "a": 1\n}\n')

    raw = target.read_bytes()
    assert raw == b'{\n  "a": 1\n}\n', raw
    assert raw.count(b"\r\n") == 0


def test_health_fallback_writer_emits_lf(tmp_path: Path) -> None:
    """`ops/health.py`'s documented fallback must not translate either.

    Its payload is `indent=2` JSON, so it is multi-line by construction and
    this site translated on every heartbeat.
    """
    from ops.health import _fallback_atomic_write_json

    target = tmp_path / "health.json"
    _fallback_atomic_write_json(target, {"alive": True, "pid": 1234})

    raw = target.read_bytes()
    assert raw.count(b"\r\n") == 0, raw
    assert raw.count(b"\n") >= 3, raw


def test_sweep_corpus_excludes_nested_checkouts() -> None:
    """The corpus is git's, so a live linked worktree cannot poison it.

    Non-vacuity for the `git ls-files` choice itself: the arm would pass
    trivially against an empty corpus, so the count floor is asserted first.
    """
    paths = _tracked_python_files()

    assert len(paths) >= MINIMUM_CHECKED, len(paths)
    intruders = [p for p in paths if p.startswith(".claude/worktrees/")]
    assert intruders == [], intruders
    assert not any(p.startswith(EXCLUDED_PREFIXES) for p in paths)
