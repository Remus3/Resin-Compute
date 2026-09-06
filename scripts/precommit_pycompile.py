"""scripts/precommit_pycompile.py - pre-commit guard.

py_compile every staged .py file before the commit lands.

WHY THIS IS ITS OWN STEP even though tools/precommit_gate.py also compiles:
the gate is FAIL-OPEN by design (it lets a commit through when it cannot run a
half of itself, so it can never wedge the repo). This guard is fail-closed on
the one condition that has no legitimate exception - a file that does not
parse. A syntax error under a windowless interpreter crashes silently at
runtime, so it must never enter history in the first place.

Install once per clone:
    python scripts/install_hooks.py       (sets core.hooksPath for you)

The repo-tracked .githooks/pre-commit shim invokes this script.
"""
from __future__ import annotations

import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def staged_python_files() -> list[Path]:
    """Files added/modified/copied/renamed in the upcoming commit.

    Deletions are excluded (--diff-filter=ACMR): a deleted file has no content
    to compile, and asking for it would fail on a perfectly correct commit.
    """
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=str(ROOT),
        text=True,
    )
    return [ROOT / line for line in out.splitlines() if line.endswith(".py")]


def main() -> int:
    files = staged_python_files()
    if not files:
        return 0
    failed: list[tuple[Path, str]] = []
    for p in files:
        if not p.exists():
            # Edge case: staged, then removed or moved before the commit ran.
            continue
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as exc:
            failed.append((p, str(exc)))
        except SyntaxError as exc:
            failed.append((p, f"{exc.__class__.__name__}: {exc}"))
    if failed:
        print(f"pre-commit: py_compile failed on {len(failed)} file(s):", file=sys.stderr)
        for p, msg in failed:
            rel = p.relative_to(ROOT) if p.is_relative_to(ROOT) else p
            print(f"  {rel}: {msg}", file=sys.stderr)
        print(
            "\nFix the syntax errors above and re-run `git commit`. To bypass\n"
            "(rarely correct), pass --no-verify.",
            file=sys.stderr,
        )
        return 1
    print(f"pre-commit: py_compile OK ({len(files)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
