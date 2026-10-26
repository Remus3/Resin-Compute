"""Every live-server test thread polls for shutdown at 0.05 s, not 0.5 s.

MAIN 2045 ORDER of 2026-10-25 (suite speed, SHA-256 verified), item 2.
`socketserver.BaseServer.serve_forever` defaults `poll_interval` to 0.5 s and
`shutdown()` waits for the next poll, so each live test paid about 0.5 s on
teardown. This arm sweeps the engine's own test modules with `ast` and fails
on any `threading.Thread(target=<x>.serve_forever, ...)` that does not pass
`kwargs={"poll_interval": <= 0.05}`.
"""

from __future__ import annotations

import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_POLL = 0.05


def _thread_sites(source: str) -> list[tuple[int, float | None]]:
    """Return (line, poll_interval or None) for each serve_forever thread."""
    sites: list[tuple[int, float | None]] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        target = next((k.value for k in node.keywords if k.arg == "target"), None)
        if not (isinstance(target, ast.Attribute) and target.attr == "serve_forever"):
            continue
        poll: float | None = None
        kw = next((k.value for k in node.keywords if k.arg == "kwargs"), None)
        if isinstance(kw, ast.Dict):
            for key, value in zip(kw.keys, kw.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "poll_interval"
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, (int, float))
                ):
                    poll = float(value.value)
        sites.append((node.lineno, poll))
    return sites


def _offenders(source: str) -> list[int]:
    return [line for line, poll in _thread_sites(source) if poll is None or poll > MAX_POLL]


def test_the_corpus_has_live_server_threads() -> None:
    total = sum(len(_thread_sites(p.read_text(encoding="utf-8"))) for p in HERE.glob("test_*.py"))
    assert total >= 3, f"expected at least 3 serve_forever threads, found {total}"


def test_every_live_server_thread_polls_fast() -> None:
    bad = {
        p.name: lines
        for p in sorted(HERE.glob("test_*.py"))
        if p.name != Path(__file__).name
        and (lines := _offenders(p.read_text(encoding="utf-8")))
    }
    assert not bad, f"serve_forever thread without poll_interval <= {MAX_POLL}: {bad}"


def test_the_detector_catches_the_default_and_a_slow_interval() -> None:
    default = "threading.Thread(target=server.serve_forever, daemon=True)\n"
    slow = "threading.Thread(target=s.serve_forever, kwargs={'poll_interval': 0.5})\n"
    fast = "threading.Thread(target=s.serve_forever, kwargs={'poll_interval': 0.05})\n"
    assert _offenders(default) == [1]
    assert _offenders(slow) == [1]
    assert _offenders(fast) == []
