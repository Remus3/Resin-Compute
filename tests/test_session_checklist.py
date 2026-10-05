"""The interactive half of FLEET-COMMON item 13: the session counter.

WHAT THIS GUARDS. Item 13 a orders every session to open with
`Session <n> checklist`, where n is this tree's session counter, kept in the
hand-off file as one `SESSION: <n>` line that `/done` rewrites to n+1.
`tools/session_checklist.py` is the SessionStart hook that reads that line and
prints ONE 7-bit line naming the counter, so the first reply has the number in
context instead of re-deriving it. The task list itself is the session's to
print; a hook that runs before the operator has typed cannot know the tasks.

THE HOOK IS READ-ONLY AND MUST NEVER RAISE. A crashing SessionStart hook noises
every session start, so a missing, duplicated or garbled counter - and an
unreadable hand-off - degrade to ONE FIXED LINE and exit 0. The fixed line
names the defect rather than inventing a number: a guessed counter is worse
than an admitted gap, because the next `/done` would then write guess+1.

NO BOX GLYPH IN ANY BYTE. Item 13 draws the box as U+2610 in chat. This tree's
tracked files are 7-bit ASCII, and hook stdout is injected as session context
through a console that may not be UTF-8, so the hook names the glyph by its
code point and never emits it. The arm below builds the glyph with chr() so
this file does not violate the rule it enforces.

EVERY DETECTOR HAS A NON-VACUITY ARM AND A SURVIVOR ARM. A parser that refused
every input would pass every degrade arm, so planted valid text must still
yield its number, and prose that merely contains the word SESSION must not be
mistaken for the counter.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / "tools" / "session_checklist.py"
HANDOFF = REPO_ROOT / "RSC-NEXT-SESSION.txt"
DONE_MD = REPO_ROOT / ".claude" / "commands" / "done.md"

#: The seed. 56 is a COMMIT-COUNT PROXY, not a session count: 55 commits touched
#: the hand-off under either of its names since 9e2bf0b, creating commit
#: included, and the counter starts one past that. The live value may only grow.
SEED = 56

#: What the hook prints when the counter is good. Anchored whole-body.
COUNTER_LINE = re.compile(r"\ASession (\d+) checklist - [ -~]+\n\Z")

#: The U+2610 BALLOT BOX, built rather than typed.
BOX = chr(0x2610)

#: The phrases done.md must carry for item 13 c and the v7 order's section 3.4.
DONE_PREFLIGHT = "every checklist task done or carried into the hand-off"
DONE_COUNTER = "SESSION: <n+1>"
DONE_UNPROMPTED = "UNPROMPTED"
DONE_ONE_LINE = "Done ritual complete, safe to clear"


def _tool():
    """The hook, loaded BY PATH: `tools/` is not imported as a package here."""
    spec = importlib.util.spec_from_file_location("session_checklist_under_test", TOOL)
    assert spec is not None and spec.loader is not None, f"cannot load {TOOL}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _handoff_text(counter_lines: list[str]) -> str:
    body = "RESINCOMPUTE - NEXT SESSION HAND-OFF\n\n  THE SESSION SCRATCHPAD IS SHARED.\n"
    return body + "".join(line + "\n" for line in counter_lines)


# ---------------------------------------------------------------------------
# render(): the pure core
# ---------------------------------------------------------------------------


def test_the_hook_reports_the_counter_from_planted_handoff_text():
    tool = _tool()
    line = tool.render(_handoff_text(["SESSION: 56"]))
    assert line.startswith("Session 56 checklist - "), line
    assert tool.render(_handoff_text(["SESSION: 1234"])).startswith("Session 1234 checklist - ")
    # Survivor: CRLF bytes from a Windows editor still read as one good line.
    assert tool.render("x\r\nSESSION: 7\r\n").startswith("Session 7 checklist - ")


def test_prose_mentioning_session_is_not_the_counter():
    """Survivor arm: the live hand-off says SESSION in prose. Only the exact
    column-0 `SESSION: <n>` line is the counter, so prose neither supplies a
    number nor counts as a duplicate."""
    tool = _tool()
    text = (
        "SESSION 9 was long.\n"
        "  THE SESSION SCRATCHPAD IS SHARED (MAIN 0905, observed).\n"
        "a SESSION: 3 quoted mid-line is prose\n"
        "SESSION: 56\n"
    )
    assert tool.render(text).startswith("Session 56 checklist - ")


@pytest.mark.parametrize(
    "counter_lines",
    [
        pytest.param([], id="missing"),
        pytest.param(["SESSION: 56", "SESSION: 57"], id="duplicate"),
        pytest.param(["SESSION: 56", "SESSION: 56"], id="duplicate-same-value"),
        pytest.param(["SESSION: fifty-six"], id="garbled-word"),
        pytest.param(["SESSION: 0"], id="garbled-zero"),
        pytest.param(["SESSION: 056"], id="garbled-leading-zero"),
        pytest.param(["SESSION:56"], id="garbled-no-space"),
        pytest.param(["SESSION: 56 (proxy)"], id="garbled-trailing-text"),
        pytest.param(["  SESSION: 56"], id="garbled-indented"),
        pytest.param(["SESSION: 56", "  SESSION: 57"], id="good-plus-indented"),
        pytest.param(["SESSION: -1"], id="garbled-negative"),
        pytest.param(["SESSION: 56", "SESSION: x"], id="good-plus-garbled"),
    ],
)
def test_a_missing_duplicate_or_garbled_counter_degrades_to_the_fixed_line(counter_lines):
    tool = _tool()
    assert tool.render(_handoff_text(counter_lines)) == tool.DEGRADED


def test_the_degraded_line_names_no_number():
    """A guessed counter is worse than an admitted gap."""
    tool = _tool()
    assert tool.DEGRADED.startswith("Session ? checklist - ")
    assert not re.search(r"\d", tool.DEGRADED.split(" - ", 1)[0])


def test_the_hook_output_is_one_seven_bit_line_with_no_box_glyph():
    tool = _tool()
    for text in (_handoff_text(["SESSION: 56"]), _handoff_text([]), None):
        line = tool.render(text)
        assert "\n" not in line and "\r" not in line, repr(line)
        assert all(32 <= ord(ch) < 127 for ch in line), repr(line)
        assert BOX not in line
    # Non-vacuity: the scan above would see the glyph if it were there.
    planted = tool.render(_handoff_text(["SESSION: 56"])) + BOX
    assert not all(32 <= ord(ch) < 127 for ch in planted)
    # And the tool's own source carries no non-ASCII byte at all.
    assert all(byte < 0x80 for byte in TOOL.read_bytes())


# ---------------------------------------------------------------------------
# main(): the hook entry point
# ---------------------------------------------------------------------------


def test_main_prints_exactly_one_line_and_exits_zero(tmp_path, capsys):
    tool = _tool()
    handoff = tmp_path / "handoff.txt"
    handoff.write_bytes(b"hand-off\nSESSION: 61\n")
    assert tool.main(handoff=handoff) == 0
    out = capsys.readouterr().out
    assert COUNTER_LINE.match(out), repr(out)
    assert COUNTER_LINE.match(out).group(1) == "61"


def test_an_unreadable_handoff_never_raises_and_exits_zero(tmp_path, capsys):
    tool = _tool()
    cases = {
        "absent": tmp_path / "no-such-file.txt",
        "a-directory": tmp_path,
    }
    non_ascii = tmp_path / "non-ascii.txt"
    non_ascii.write_bytes(b"SESSION: 56\n\xe2\x98\x90 /done\n")
    cases["non-ascii"] = non_ascii
    for label, path in cases.items():
        assert tool.main(handoff=path) == 0, label
        out = capsys.readouterr().out
        assert out == tool.DEGRADED + "\n", (label, out)


def test_the_hook_writes_nothing(tmp_path, capsys):
    """Read-only: the hand-off bytes and its directory are unchanged."""
    tool = _tool()
    handoff = tmp_path / "handoff.txt"
    handoff.write_bytes(b"SESSION: 9\n")
    before = sorted(p.name for p in tmp_path.iterdir())
    tool.main(handoff=handoff)
    capsys.readouterr()
    assert handoff.read_bytes() == b"SESSION: 9\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == before


#: The runtime imports the hook may make: stdlib only, and no kit module.
ALLOWED_IMPORTS = frozenset({"__future__", "re", "sys", "pathlib"})


def _imported_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    return roots


def test_the_tool_imports_no_kit_file():
    """The hook imports no kit file and nothing outside the stdlib set above.
    Read by AST, so a docstring that MENTIONS the kit is not an import."""
    roots = _imported_roots(TOOL.read_text(encoding="ascii"))
    assert roots, "the AST walk found no import at all, so it examined nothing"
    assert roots <= ALLOWED_IMPORTS, f"unexpected imports: {sorted(roots - ALLOWED_IMPORTS)}"
    assert "importlib" not in roots and "runpy" not in roots


def test_the_import_sweep_fires_on_a_planted_kit_import():
    planted = '"""mentions ops/fleet_kit only in prose"""\nimport sys\n'
    assert _imported_roots(planted) == {"sys"}
    for source in ("from ops.fleet_kit import fleet_checklist\n", "import fleet_checklist\n"):
        assert not _imported_roots(source) <= ALLOWED_IMPORTS, source


def test_the_hook_survives_cwd_drift(tmp_path):
    """Launched from an unrelated directory, it still finds the hand-off,
    because the path is resolved from __file__ and never from the cwd."""
    env = dict(os.environ)
    env["RESINCOMPUTE_RUNTIME_DIR"] = str(tmp_path / "runtime")
    completed = subprocess.run(
        [sys.executable, str(TOOL)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    out = completed.stdout.decode("ascii")
    match = COUNTER_LINE.match(out.replace("\r\n", "\n"))
    assert match, repr(out)
    assert int(match.group(1)) == _live_counter()
    assert sorted(p.name for p in tmp_path.iterdir()) == [], "the hook wrote into its cwd"


# ---------------------------------------------------------------------------
# The live hand-off
# ---------------------------------------------------------------------------


def _live_counter() -> int:
    lines = HANDOFF.read_bytes().decode("ascii").split("\n")
    hits = [line for line in lines if line.lstrip().startswith("SESSION:")]
    assert len(hits) == 1, f"RSC-NEXT-SESSION.txt carries {len(hits)} SESSION lines: {hits}"
    match = re.fullmatch(r"SESSION: ([1-9][0-9]*)", hits[0])
    assert match, f"the SESSION line is malformed: {hits[0]!r}"
    return int(match.group(1))


def test_the_live_handoff_carries_exactly_one_session_counter():
    assert _live_counter() >= SEED, "the session counter went backwards past its seed"


# ---------------------------------------------------------------------------
# done.md: item 13 c and v7 section 3.4
# ---------------------------------------------------------------------------


def _done_missing(text: str) -> list[str]:
    return [p for p in (DONE_PREFLIGHT, DONE_COUNTER, DONE_UNPROMPTED, DONE_ONE_LINE) if p not in text]


def test_done_md_carries_the_preflight_the_counter_and_the_unprompted_rule():
    text = DONE_MD.read_bytes().decode("ascii")
    assert _done_missing(text) == []
    # The one line stays the only chat output, in a fence of its own.
    assert "```\n" + DONE_ONE_LINE + "\n```" in text


def test_the_done_md_sweep_fires_on_a_planted_omission():
    full = "\n".join((DONE_PREFLIGHT, DONE_COUNTER, DONE_UNPROMPTED, DONE_ONE_LINE))
    assert _done_missing(full) == []
    assert _done_missing(full.replace(DONE_PREFLIGHT, "")) == [DONE_PREFLIGHT]
    assert _done_missing(full.replace(DONE_COUNTER, "SESSION: n")) == [DONE_COUNTER]
    assert _done_missing("") == [DONE_PREFLIGHT, DONE_COUNTER, DONE_UNPROMPTED, DONE_ONE_LINE]
