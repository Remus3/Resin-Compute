"""/done must accept either spelling of `core.hooksPath` (slice 0z).

WHY THIS EXISTS. `.claude/commands/done.md` section 0 said `git config
core.hooksPath` "must print `.githooks`" - a byte-equal check. Sessions 58, 60,
64, 68 and 71 each saw it read back as the ABSOLUTE `<main root>\\.githooks`
and re-ran `scripts/install_hooks.py` as if the hooks were broken. Root cause
(session 72): Claude Code's own worktree setup rewrites a relative
`core.hooksPath` to the absolute main-root path with a plain `git config`
from the linked worktree; with no `extensions.worktreeConfig` that lands in
the shared `.git/config`. Both spellings name the same directory, and
`scripts/install_hooks.py` already RESOLVES the value (`_names_hooks_dir`), so
the drift is harmless. The ritual step must resolve too.

Rejected alternative: `extensions.worktreeConfig`, which would leave every
agent worktree with no hooks at all.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DONE_MD = REPO_ROOT / ".claude" / "commands" / "done.md"

#: The section 0 bullet before slice 0z, verbatim.
PRE_FIX_BULLET = (
    "- `git config core.hooksPath` must print `.githooks`. If it prints nothing, run\n"
    "  `python scripts/install_hooks.py` first.\n"
)


def _hookspath_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for chunk in text.split("\n- "):
        if "core.hooksPath" in chunk and "install_hooks.py" in chunk:
            bullets.append(chunk)
    return bullets


def _demands_byte_equal_spelling(bullet: str) -> bool:
    """True when the bullet accepts only the relative spelling."""
    accepts_resolution = "resolve" in bullet.lower() and "absolute" in bullet.lower()
    return not accepts_resolution


def test_done_md_hookspath_step_accepts_either_spelling() -> None:
    bullets = _hookspath_bullets(DONE_MD.read_text(encoding="utf-8"))
    assert bullets, "done.md lost its core.hooksPath / install_hooks.py step"
    offenders = [b for b in bullets if _demands_byte_equal_spelling(b)]
    assert offenders == [], (
        "done.md demands the byte-equal `.githooks` spelling; it must accept any "
        f"value that RESOLVES to <repo>/.githooks, absolute included: {offenders!r}"
    )


def test_done_md_still_runs_install_hooks_when_unresolved() -> None:
    """Neighbour arm: the fix narrows the check, it must not delete it."""
    (bullet,) = _hookspath_bullets(DONE_MD.read_text(encoding="utf-8"))
    assert "python scripts/install_hooks.py" in bullet
    assert ".githooks" in bullet


def test_detector_rejects_the_pre_fix_bullet() -> None:
    """Non-vacuity arm: the predicate fires on the wording 0z replaced."""
    assert _demands_byte_equal_spelling(PRE_FIX_BULLET)
