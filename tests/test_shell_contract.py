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
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from core import ports

REPO_ROOT = Path(__file__).resolve().parent.parent
SHELL_DIR = REPO_ROOT / "shell"

#: Everything tracked under shell/. node_modules is gitignored and enormous.
def _shell_sources() -> list[Path]:
    out: list[Path] = []
    for path in SHELL_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(SHELL_DIR).as_posix()
        if rel.startswith("node_modules/") or "/node_modules/" in rel:
            continue
        if path.suffix in {".js", ".json", ".md"} or path.name == ".gitignore":
            out.append(path)
    return out


def test_the_shell_directory_exists_and_has_sources():
    """Non-vacuity. A sweep that silently found nothing would pass forever."""
    sources = _shell_sources()
    assert len(sources) >= 8, f"only found {len(sources)} shell sources"
    names = {p.name for p in sources}
    assert {"main.js", "preload.js", "package.json", "tray.js"} <= names


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
