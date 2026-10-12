"""Guard the hand-restored win32 marker on colorama in requirements-dev.txt.

Why: pip-compile drops pytest's `sys_platform == "win32"` marker on colorama,
and a Linux recompile (Dependabot) drops colorama entirely. Either way CI stays
green on Linux while a Windows `pip install --require-hashes` breaks. The
restore rule lives in the comment block of requirements-dev.in; before this
file nothing tested it (session 68 finding, RSC-NEXT-SESSION item 1).

The required line is exactly `colorama==0.4.6 ; sys_platform == "win32"`
followed by its hash continuation lines. Stdlib only.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK = REPO_ROOT / "requirements-dev.txt"

#: The exact requirement head the .in comment tells a human to restore.
REQUIRED_HEAD = 'colorama==0.4.6 ; sys_platform == "win32"'

_HASH_RE = re.compile(r"--hash=sha256:[0-9a-f]{64}")


def _requirement_blocks(text: str) -> dict[str, str]:
    """Map lower-cased project name -> its logical requirement line.

    Joins backslash continuations; skips comment and blank lines.
    """
    blocks: dict[str, str] = {}
    current: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not current and (not line or line.lstrip().startswith("#")):
            continue
        current.append(line.rstrip("\\").strip())
        if line.endswith("\\"):
            continue
        logical = " ".join(current)
        current = []
        name = re.split(r"[=<>!~ ;\[]", logical, maxsplit=1)[0].lower()
        blocks[name] = logical
    return blocks


def colorama_problems(text: str) -> list[str]:
    """Return every way `text` fails the colorama marker contract."""
    blocks = _requirement_blocks(text)
    entry = blocks.get("colorama")
    if entry is None:
        return ["colorama is missing (a Linux recompile drops it)"]
    problems: list[str] = []
    head = entry.split(" --hash=", 1)[0].strip()
    if head != REQUIRED_HEAD:
        problems.append(f"colorama head is {head!r}, want {REQUIRED_HEAD!r}")
    if not _HASH_RE.search(entry):
        problems.append("colorama carries no sha256 hash")
    return problems


def test_colorama_line_keeps_win32_marker() -> None:
    text = LOCK.read_text(encoding="utf-8")
    assert colorama_problems(text) == []


def test_exactly_one_colorama_requirement_head() -> None:
    text = LOCK.read_text(encoding="utf-8")
    heads = [
        ln for ln in text.splitlines() if ln.lower().startswith("colorama")
    ]
    assert heads == [REQUIRED_HEAD + " \\"]


# --- non-vacuity arms: reinstate each defect on a copy and prove it reds ---


def test_arm_reds_when_marker_stripped() -> None:
    text = LOCK.read_text(encoding="utf-8")
    assert REQUIRED_HEAD in text
    stripped = text.replace(REQUIRED_HEAD, "colorama==0.4.6", 1)
    assert colorama_problems(stripped) != []


def test_arm_reds_when_marker_wrong_platform() -> None:
    text = LOCK.read_text(encoding="utf-8")
    bad = text.replace('"win32"', '"linux"', 1)
    assert colorama_problems(bad) != []


def test_arm_reds_when_colorama_dropped() -> None:
    text = LOCK.read_text(encoding="utf-8")
    kept = []
    skipping = False
    for line in text.splitlines():
        if line.startswith("colorama"):
            skipping = True
            continue
        if skipping and line.startswith((" ", "\t")):
            continue
        skipping = False
        kept.append(line)
    dropped = "\n".join(kept) + "\n"
    assert "colorama==" not in dropped
    assert colorama_problems(dropped) == [
        "colorama is missing (a Linux recompile drops it)"
    ]


def test_arm_reds_when_hashes_lost() -> None:
    text = LOCK.read_text(encoding="utf-8")
    start = text.index(REQUIRED_HEAD)
    end = text.index("# via pytest", start)
    block = _HASH_RE.sub("--hash=sha256:x", text[start:end])
    bad = text[:start] + block + text[end:]
    assert colorama_problems(bad) == ["colorama carries no sha256 hash"]


def test_neighbours_parse_cleanly() -> None:
    """Legitimate neighbours survive: the parser still sees every pin."""
    blocks = _requirement_blocks(LOCK.read_text(encoding="utf-8"))
    for name in ("pytest", "iniconfig", "mypy", "ruff", "pytest-timeout"):
        assert name in blocks, name
        assert _HASH_RE.search(blocks[name]), name
