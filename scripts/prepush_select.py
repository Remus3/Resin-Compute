"""Pick the application-suite modules a push can plausibly affect.

MAIN 2246 ORDER section 2, PERF-AUDIT item 1. `.githooks/pre-push` used to run
both whole suites serially on every push (about 230 s; a low-memory run went
red). It now runs ruff, the engine suite, and the application modules this
script selects. The whole application suite runs in CI and on the nightly
schedule, so this is a fast local gate, not the only one.

THE MAPPING, deterministic and bounded:

  1. Changed paths = `git diff --name-only <base>...HEAD`, plus `<base> HEAD`
     (a force-push discards the remote's own side; 0i 2c residue b), plus the
     working tree's own edits against HEAD and its untracked, non-ignored
     files (the hook grades the working tree; 0i 2c residue a).
     <base> is `--base` when it names a commit, else `@{u}`. No base -> FULL.
  2. More than MAX_CHANGED paths, or any FULL_TRIGGERS path -> FULL.
  3. A changed `tests/test_*.py` that exists runs itself.
  4. Every other changed path maps to each `tests/test_*.py` whose text holds
     one of its needles (`needles_for`), found with one `git grep -F`.
  5. Plumbing modules (tests/_markers.py PLUMBING) reached ONLY through step 4
     are dropped unless a changed path sits under a PLUMBING_ROOTS root.
  6. pytest's own last-failed cache adds its `tests/` modules (the `--lf`
     half of the order).
  7. CI_ONLY modules reached ONLY through step 4 are deferred to CI (MAIN
     2246 ORDER s2 item 2c, the 30 s target); steps 3 and 6 still run them.
  8. Nothing selected -> NONE.

THE ENGINE SUITE (0i 2c, the 30 s target; `engine_decision`). Profiled
2026-10-12 on this host (Python 3.14), a one-file plumbing push spent 24 s in
the application selection and 9.4 s in `pytest agents/pity_engine`, which no
plumbing file can reach. The engine suite's verdict is a function of the files
it imports (`engine_closure`: an AST walk from every `.py` under
`agents/pity_engine/` plus the root `conftest.py`, nested and try-imports
included), the pytest configuration, and the interpreter. So it is SKIPPED
locally only when no changed path is: under `agents/`; in the closure; a
non-Python file beside a closure module; a root-level module or a path whose
top-level name shadows any module the closure imports; a FULL trigger; a
root pytest config file (ENGINE_CONFIG_FILES); a deleted or renamed-away
`.py` (the diff runs with --no-renames so both halves are listed). A
last-failed engine test, no base, more than MAX_CHANGED paths, or any walker
error -> RUN. CI's "Engine suite" step (.github/workflows/ci.yml) runs it on
every push and pull request regardless, and push runs are never cancelled.

OUTPUT, four lines on stdout, read by the hook:

    <FULL|SELECT|NONE>
    <one-line reason>
    <comma-joined module paths, empty unless SELECT>
    <RUN|SKIP> <one-line reason>     (the engine suite; only SKIP skips)

`--ci-mark` prints one line instead: the `-m` expression ci.yml's push and
pull-request jobs pass to the application suite - "not plumbing", or empty
for every module (see `ci_mark_for`).

Any internal error prints FULL with the error's type as the reason and exits
0, so a broken selector costs time and never coverage. Stdlib only.
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
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
        # pytest 9 reads these two BEFORE pytest.ini (findpaths.locate_config).
        "pytest.toml",
        ".pytest.toml",
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

#: CI-ONLY (MAIN 2246 ORDER s2 item 2c). Modules the pre-push gate never
#: reaches through the needle mapping (step 4): each one is an exhaustive
#: sweep, census, mutation campaign or end-to-end hook harness that spawns
#: real git / sh / pytest children, and together they were about two thirds
#: of a plumbing push's selected time (measured 2026-10-10, this host, Python
#: 3.14: a tools/precommit_gate.py push selected 24 modules, 84 s, of which
#: these six were 61 s). CI runs every one of them: the product-class ones on
#: every push, the PLUMBING ones whenever a plumbing root changed, which is
#: the only time the hook would have mapped them. A CI-only module still runs
#: locally when its own file changed (step 3) or it last failed (step 6).
#: Re-measure with `--durations=0` before adding or removing an entry.
CI_ONLY: frozenset[str] = frozenset(
    {
        "tests/test_hook_gate.py",
        "tests/test_conftest_git_gate_sites.py",
        "tests/test_git_subprocess_census.py",
        "tests/test_git_env_scrub.py",
        "tests/test_gate_mutation_runner.py",
        "tests/test_responder_gate_census.py",
    }
)

_ZERO_SHA = "0" * 40

#: The engine-suite verdicts on the fourth output line. The hook skips the
#: engine suite on the exact first word SKIP and runs it on anything else.
ENGINE_RUN = "RUN"
ENGINE_SKIP = "SKIP"

#: The engine suite's target, and the root under which every file pytest
#: loads for it (package inits, conftests, the tests) lives.
ENGINE_SUITE = "agents/pity_engine"
ENGINE_PREFIX = "agents/"

#: Root files pytest may read as its configuration besides pytest.ini (a
#: FULL trigger). Any change to one, including creating it, runs the engine.
ENGINE_CONFIG_FILES = frozenset({"tox.ini", "pyproject.toml", "setup.cfg", ".pytest.ini"})


@dataclass(frozen=True)
class Selection:
    mode: str
    reason: str
    modules: tuple[str, ...] = ()
    engine: str = ENGINE_RUN
    engine_reason: str = ""


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
    ci_only: frozenset[str] = frozenset(),
) -> Selection:
    """The pure decision. `grep` maps needles to the test modules holding any.

    `ci_only` modules reached only through the mapping are deferred to CI;
    `compute` passes CI_ONLY, the pure default defers nothing.
    """
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
    deferred = (mapped & ci_only) - explicit - failed
    mapped -= deferred
    modules = tuple(sorted(explicit | mapped | failed))
    deferred_note = f", {len(deferred)} CI-only deferred" if deferred else ""

    unsafe = [m for m in modules if any(ch.isspace() or ch == "," for ch in m)]
    if unsafe:
        return Selection(FULL, f"module path the hook cannot split: {unsafe[0]!r}")
    if not modules:
        return Selection(
            NONE,
            f"no application module maps to {len(changed)} changed path(s)"
            f"{deferred_note}",
        )
    return Selection(
        SELECT,
        f"{len(modules)} module(s) from {len(changed)} changed path(s)"
        f"{'' if plumbing_touched else ', plumbing deselected'}"
        f"{f', {len(failed)} last-failed' if failed else ''}"
        f"{deferred_note}",
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


def _module_files(root: Path, dotted: str) -> list[str]:
    """Repo files executed by importing `dotted`: each package `__init__.py` on
    the way down plus the module itself. Empty when it is not in the repo."""
    parts = [p for p in dotted.split(".") if p]
    found: list[str] = []
    for i in range(1, len(parts) + 1):
        rel = "/".join(parts[:i])
        if (root / rel / "__init__.py").is_file():
            found.append(f"{rel}/__init__.py")
        elif (root / f"{rel}.py").is_file():
            found.append(f"{rel}.py")
            break
        elif not (root / rel).is_dir():
            break
        # else: a namespace package (a directory with no __init__.py, as
        # `ops/loop/` is) - nothing executes, keep descending.
    return found


def _imports_of(root: Path, rel: str) -> tuple[set[str], set[str]]:
    """(repo files `rel` imports, top-level names it imports). Every Import and
    ImportFrom node counts, nested and guarded ones included. Raises on a file
    that does not parse, which the caller turns into RUN."""
    tree = ast.parse((root / rel).read_bytes(), filename=rel)
    # Both a module and a package `__init__.py` resolve relative imports
    # against the directory holding them.
    package = PurePosixPath(rel).parent.parts
    files: set[str] = set()
    tops: set[str] = set()

    def absolute(dotted: str) -> None:
        resolved = _module_files(root, dotted)
        files.update(resolved)
        top = dotted.split(".", 1)[0]
        if not resolved and not (root / top).is_dir():
            tops.add(top)  # stdlib or third party: a repo file could shadow it

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                absolute(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                anchor = list(package[: len(package) - (node.level - 1)])
                base = ".".join([*anchor, *([node.module] if node.module else [])])
                files.update(_module_files(root, base))
            else:
                base = node.module or ""
                absolute(base)
            for alias in node.names:
                files.update(_module_files(root, f"{base}.{alias.name}" if base else alias.name))
    return files, tops


def engine_closure(root: Path = REPO_ROOT) -> tuple[frozenset[str], frozenset[str]]:
    """(repo files the engine suite imports, external top-level names it imports).

    The external names are the stdlib and third-party ones - those a new repo
    file of the same name at the root would shadow on sys.path[0].

    Seeds: every `.py` under ENGINE_SUITE, its ancestor package inits and the
    root `conftest.py`. Walked to
    a fixed point over the repo's own files; stdlib and third-party names are
    collected but not followed.
    """
    seeds = {"conftest.py"} if (root / "conftest.py").is_file() else set()
    # pytest imports every ancestor package of a test module.
    seeds |= set(_module_files(root, ENGINE_SUITE.replace("/", ".")))
    seeds |= {
        p.relative_to(root).as_posix()
        for p in (root / ENGINE_SUITE).rglob("*.py")
        if "__pycache__" not in p.parts
    }
    seen: set[str] = set()
    tops: set[str] = set()
    todo = sorted(seeds)
    while todo:
        rel = todo.pop()
        if rel in seen:
            continue
        seen.add(rel)
        files, names = _imports_of(root, rel)
        tops |= names
        todo.extend(f for f in files if f not in seen)
    return frozenset(seen), frozenset(tops)


def engine_decision(
    changed: Sequence[str],
    *,
    closure: frozenset[str],
    top_names: frozenset[str],
    last_failed: Iterable[str],
    deleted: Iterable[str] = (),
) -> tuple[str, str]:
    """RUN or SKIP for the local engine suite, with a one-line reason.

    `deleted` are changed paths absent from the working tree. The closure is
    walked over the working tree, so a deleted (or, with renames off, the old
    half of a renamed) engine dependency is invisible to it: any deleted
    `.py` therefore runs the engine (adversary round 1, 2026-10-12).
    """
    changed = sorted(set(changed))
    gone = sorted(d for d in set(deleted) if d.endswith(".py"))
    if len(changed) > MAX_CHANGED:
        return ENGINE_RUN, f"{len(changed)} changed paths exceed MAX_CHANGED={MAX_CHANGED}"
    failed = sorted(m for m in last_failed if m.startswith(ENGINE_PREFIX))
    if failed:
        return ENGINE_RUN, f"last-failed engine test(s): {failed[0]}"
    # The repo root holds the root conftest, but its other files (docs, the
    # hand-off) are not data the engine reads; the root-level cases that do
    # matter are the FULL triggers and root `.py` files, handled below.
    closure_dirs = {str(PurePosixPath(f).parent) for f in closure} - {"."}
    for c in changed:
        p = PurePosixPath(c)
        top = p.parts[0].removesuffix(".py") if p.parts else ""
        if c in FULL_TRIGGERS:
            why = "a FULL trigger"
        elif c in ENGINE_CONFIG_FILES:
            why = "a root pytest configuration file"
        elif c in gone:
            why = "a deleted or renamed-away Python file"
        elif c.startswith(ENGINE_PREFIX):
            why = f"under {ENGINE_PREFIX}"
        elif c in closure:
            why = "in the engine's import closure"
        elif len(p.parts) == 1 and p.suffix == ".py":
            why = "a root-level module on sys.path[0]"
        elif top in top_names:
            why = f"it shadows the imported name {top!r}"
        elif p.suffix != ".py" and str(p.parent) in closure_dirs:
            why = "a data file beside an engine-closure module"
        else:
            continue
        return ENGINE_RUN, f"{c} is {why}"
    return (
        ENGINE_SKIP,
        f"no changed path reaches the engine closure ({len(closure)} files); CI runs it",
    )


def render(selection: Selection) -> str:
    engine = f"{selection.engine} {selection.engine_reason}".rstrip()
    return "\n".join(
        [selection.mode, selection.reason, ",".join(selection.modules), engine]
    )


def _last_failed_keys(cache_file: Path) -> set[str]:
    """Module paths named in pytest's lastfailed cache; empty on any defect."""
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    if not isinstance(data, dict):
        return set()
    return {
        key.split("::", 1)[0].replace("\\", "/") for key in data if isinstance(key, str)
    }


def last_failed_modules(cache_file: Path) -> set[str]:
    """`tests/` modules named in pytest's lastfailed cache; empty on any defect."""
    return {m for m in _last_failed_keys(cache_file) if _is_test_module(m)}


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
    # --no-renames: a rename must list its OLD path too, or a renamed-away
    # module disappears from every rule (adversary round 1, 2026-10-12).
    pushed = _git(root, "diff", "--name-only", "--no-renames", f"{resolved}...HEAD")
    # 0i(2c) residue (b): a FORCE-PUSH moves the remote from <base> to HEAD,
    # so the remote's real change is the two-dot diff. The three-dot one above
    # lists only HEAD's side since the merge-base and misses a remote-only
    # change the force-push discards. On a fast-forward the two are equal.
    replaced = _git(root, "diff", "--name-only", "--no-renames", resolved, "HEAD")
    local = _git(root, "diff", "--name-only", "--no-renames", "HEAD")
    # 0i(2c) residue (a): the hook grades the files ON DISK, and pytest reads
    # its configuration and conftests from disk, so an untracked file counts.
    # Gitignored files do not: they are scratch the tree has disowned.
    untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    if pushed is None or replaced is None or local is None or untracked is None:
        return None
    return [
        line for line in (pushed + replaced + local + untracked).splitlines() if line.strip()
    ]


def compute(root: Path, base: str | None) -> Selection:
    changed = _changed(root, base)
    if changed is None:
        return Selection(
            FULL,
            "no upstream or base commit to diff against, or git diff failed",
            engine_reason="no base to diff against",
        )
    failed_keys = _last_failed_keys(root / ".pytest_cache" / "v" / "cache" / "lastfailed")
    selection = select(
        changed,
        grep=_git_grep(root),
        exists=lambda rel: (root / rel).is_file(),
        plumbing=load_plumbing(root),
        last_failed={m for m in failed_keys if _is_test_module(m)},
        ci_only=CI_ONLY,
    )
    try:
        closure, top_names = engine_closure(root)
        engine, engine_reason = engine_decision(
            changed,
            closure=closure,
            top_names=top_names,
            last_failed=failed_keys,
            deleted=[c for c in changed if not (root / c).exists()],
        )
    except Exception as exc:  # noqa: BLE001 - any walker defect must degrade to RUN
        engine, engine_reason = ENGINE_RUN, f"engine closure error: {type(exc).__name__}"
    return dataclasses.replace(selection, engine=engine, engine_reason=engine_reason)


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
