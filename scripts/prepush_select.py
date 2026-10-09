"""Pick the application-suite modules a push can plausibly affect.

MAIN 2246 ORDER section 2, PERF-AUDIT item 1. `.githooks/pre-push` used to run
both whole suites serially on every push (about 230 s; a low-memory run went
red). It now runs ruff, the engine suite, and the application modules this
script selects. The whole application suite runs in CI and on the nightly
schedule, so this is a fast local gate, not the only one.

THE MAPPING, deterministic and bounded:

  1. Changed paths = `git diff --name-only <base>...HEAD` plus the working
     tree's own edits against HEAD (the hook grades the working tree).
     <base> is `--base` when it names a commit, else `@{u}`. No base -> FULL.
  2. More than MAX_CHANGED paths, or any FULL_TRIGGERS path -> FULL.
  3. A changed `tests/test_*.py` that exists runs itself.
  4. Every other changed path maps to each `tests/test_*.py` whose text holds
     one of its needles (`needles_for`), found with one `git grep -F`.
  5. Plumbing modules (tests/_markers.py PLUMBING) reached ONLY through step 4
     are dropped unless a changed path sits under a PLUMBING_ROOTS root.
  6. pytest's own last-failed cache adds its `tests/` modules (the `--lf`
     half of the order).
  7. Nothing selected -> NONE.

OUTPUT, three lines on stdout, read by the hook:

    <FULL|SELECT|NONE>
    <one-line reason>
    <comma-joined module paths, empty unless SELECT>

`--ci-mark` prints one line instead: the `-m` expression ci.yml's push and
pull-request jobs pass to the application suite - "not plumbing", or empty
for every module (see `ci_mark_for`).

Any internal error prints FULL with the error's type as the reason and exits
0, so a broken selector costs time and never coverage. Stdlib only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parent.parent

FULL = "FULL"
SELECT = "SELECT"
NONE = "NONE"

#: Above this many changed paths the mapping stops being cheaper or clearer
#: than the whole suite.
MAX_CHANGED = 40

#: A change to any of these can alter what EVERY module collects or how it
#: runs, so no per-module mapping is trustworthy.
FULL_TRIGGERS = frozenset(
    {
        "conftest.py",
        "pytest.ini",
        "requirements.txt",
        "requirements-dev.txt",
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/_markers.py",
    }
)

#: Basenames too common to identify anything.
GENERIC_BASENAMES = frozenset({"__init__.py", "__main__.py", "conftest.py"})

#: Mirrors tests/_markers.py PLUMBING_ROOTS; `load_plumbing` checks the two agree.
PLUMBING_ROOTS: tuple[str, ...] = (
    "tools/",
    "headless/",
    "scripts/",
    "ops/",
    ".githooks/",
    ".github/",
    ".claude/",
)

_ZERO_SHA = "0" * 40


@dataclass(frozen=True)
class Selection:
    mode: str
    reason: str
    modules: tuple[str, ...] = ()


def _is_test_module(path: str) -> bool:
    p = PurePosixPath(path)
    return (
        len(p.parts) == 2
        and p.parts[0] == "tests"
        and p.name.startswith("test_")
        and p.suffix == ".py"
    )


def needles_for(path: str) -> list[str]:
    """The fixed strings whose presence in a test module ties it to `path`."""
    p = PurePosixPath(path)
    needles = [path]
    if p.name not in GENERIC_BASENAMES and p.name != path:
        needles.append(p.name)
    if p.suffix == ".py":
        stem_path = path[: -len(".py")]
        if p.name == "__init__.py":
            package = str(p.parent)
            if package not in (".", "") and "/" in package:
                needles.append(package.replace("/", "."))
        else:
            needles.append(stem_path)
            needles.append(stem_path.replace("/", "."))
            needles.append(f"import {p.stem}")
            needles.append(f"from {p.stem} import")
    return needles


def select(
    changed: Sequence[str],
    *,
    grep: Callable[[Sequence[str]], set[str]],
    exists: Callable[[str], bool],
    plumbing: frozenset[str],
    last_failed: Iterable[str],
) -> Selection:
    """The pure decision. `grep` maps needles to the test modules holding any."""
    changed = sorted(set(changed))
    if len(changed) > MAX_CHANGED:
        return Selection(FULL, f"{len(changed)} changed paths exceed MAX_CHANGED={MAX_CHANGED}")
    triggers = [c for c in changed if c in FULL_TRIGGERS]
    if triggers:
        return Selection(FULL, f"changed FULL trigger(s): {', '.join(triggers)}")

    explicit = {c for c in changed if _is_test_module(c) and exists(c)}
    needles: list[str] = []
    for c in changed:
        if _is_test_module(c):
            continue
        needles.extend(needles_for(c))
    mapped = set(grep(needles)) if needles else set()

    plumbing_touched = any(c.startswith(PLUMBING_ROOTS) for c in changed)
    if not plumbing_touched:
        mapped -= plumbing

    failed = {m for m in last_failed if _is_test_module(m) and exists(m)}
    modules = tuple(sorted(explicit | mapped | failed))

    unsafe = [m for m in modules if any(ch.isspace() or ch == "," for ch in m)]
    if unsafe:
        return Selection(FULL, f"module path the hook cannot split: {unsafe[0]!r}")
    if not modules:
        return Selection(
            NONE,
            f"no application module maps to {len(changed)} changed path(s)",
        )
    return Selection(
        SELECT,
        f"{len(modules)} module(s) from {len(changed)} changed path(s)"
        f"{'' if plumbing_touched else ', plumbing deselected'}"
        f"{f', {len(failed)} last-failed' if failed else ''}",
        modules,
    )


def ci_mark_for(changed: Sequence[str]) -> str:
    """The `-m` expression for a CI push or pull-request run over `changed`.

    "not plumbing" only when the diff is bounded and touches neither a
    plumbing root nor a FULL trigger; otherwise "" - every module runs.
    """
    changed = sorted(set(changed))
    if len(changed) > MAX_CHANGED:
        return ""
    if any(c in FULL_TRIGGERS or c.startswith(PLUMBING_ROOTS) for c in changed):
        return ""
    return "not plumbing"


def render(selection: Selection) -> str:
    return "\n".join([selection.mode, selection.reason, ",".join(selection.modules)])


def last_failed_modules(cache_file: Path) -> set[str]:
    """`tests/` modules named in pytest's lastfailed cache; empty on any defect."""
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    if not isinstance(data, dict):
        return set()
    out = set()
    for key in data:
        if not isinstance(key, str):
            continue
        module = key.split("::", 1)[0].replace("\\", "/")
        if _is_test_module(module):
            out.add(module)
    return out


def load_plumbing(root: Path = REPO_ROOT) -> frozenset[str]:
    """PLUMBING from `<root>/tests/_markers.py`, loaded by path, never via `tests`."""
    registry = root / "tests" / "_markers.py"
    if not registry.is_file():
        return frozenset()
    spec = importlib.util.spec_from_file_location("_rsc_test_markers", registry)
    if spec is None or spec.loader is None:
        return frozenset()
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if tuple(module.PLUMBING_ROOTS) != PLUMBING_ROOTS:
        raise RuntimeError("tests/_markers.py PLUMBING_ROOTS drifted from the selector's")
    return frozenset(module.PLUMBING)


def _git(root: Path, *args: str, ok: Sequence[int] = (0,)) -> str | None:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    if completed.returncode not in ok:
        return None
    return completed.stdout


def _resolve_base(root: Path, base: str | None) -> str | None:
    for candidate in (base, "@{u}"):
        if not candidate or candidate == _ZERO_SHA:
            continue
        out = _git(root, "rev-parse", "--verify", "-q", f"{candidate}^{{commit}}")
        if out and out.strip():
            return out.strip()
    return None


def _git_grep(root: Path) -> Callable[[Sequence[str]], set[str]]:
    def grep(needles: Sequence[str]) -> set[str]:
        args = ["grep", "-l", "-F"]
        for needle in dict.fromkeys(needles):
            args += ["-e", needle]
        out = _git(root, *args, "--", "tests/test_*.py", ok=(0, 1))
        if out is None:
            raise RuntimeError("git grep failed")
        return {line.strip() for line in out.splitlines() if _is_test_module(line.strip())}

    return grep


def _changed(root: Path, base: str | None) -> list[str] | None:
    resolved = _resolve_base(root, base)
    if resolved is None:
        return None
    pushed = _git(root, "diff", "--name-only", f"{resolved}...HEAD")
    local = _git(root, "diff", "--name-only", "HEAD")
    if pushed is None or local is None:
        return None
    return [line for line in (pushed + local).splitlines() if line.strip()]


def compute(root: Path, base: str | None) -> Selection:
    changed = _changed(root, base)
    if changed is None:
        return Selection(FULL, "no upstream or base commit to diff against, or git diff failed")
    return select(
        changed,
        grep=_git_grep(root),
        exists=lambda rel: (root / rel).is_file(),
        plumbing=load_plumbing(root),
        last_failed=last_failed_modules(root / ".pytest_cache" / "v" / "cache" / "lastfailed"),
    )


def _emit(text: str) -> None:
    """LF-only bytes: a CR from Windows text-mode stdout would reach the hook's
    `read` and turn SELECT into an unknown mode."""
    sys.stdout.flush()
    sys.stdout.buffer.write((text + "\n").encode("ascii", "replace"))
    sys.stdout.buffer.flush()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default=None, help="commit to diff against (default @{u})")
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository root")
    parser.add_argument(
        "--ci-mark",
        action="store_true",
        help="print only the -m expression for a CI run ('' = every module)",
    )
    args = parser.parse_args(argv)
    if args.ci_mark:
        try:
            changed = _changed(Path(args.root), args.base)
            mark = "" if changed is None else ci_mark_for(changed)
        except Exception:  # noqa: BLE001 - any defect here must degrade to every module
            mark = ""
        _emit(mark)
        return 0
    try:
        selection = compute(Path(args.root), args.base)
    except Exception as exc:  # noqa: BLE001 - any defect here must degrade to FULL
        selection = Selection(FULL, f"selector error: {type(exc).__name__}")
    _emit(render(selection))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
