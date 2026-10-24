"""`tools/roots_map_probe.py` - ADR-013 interim d, the session-start probe.

Every arm runs under tmp_path: the roots map, MAIN's tree and the probe's
state file are all built there and handed to the probe by argument, so no arm
reads this host's real map or writes this tree's real control directory.

The arms, by the slice D contract:

- drift is reported against the previous reading, and NOT reported when
  nothing moved (the non-vacuity pair);
- the probe writes nothing except its own state file under the control dir;
- a missing, unparseable or MAIN-less map degrades to one friendly line, no
  traceback, exit 0;
- no output line carries a directory path, an account path or an email.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

probe = importlib.import_module("tools.roots_map_probe")
responder = importlib.import_module("tools.moon_sync_responder")

_ACCOUNT_PATH = re.compile(
    r"(?:[A-Za-z]:\\Users\\[^\\\s]+)|(?:/home/[^/\s]+)|(?:/Users/[^/\s]+)",
)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def _main_tree(tmp_path: Path, notes: tuple[str, ...] = ("a-from-MAIN-ORDER.txt",)) -> Path:
    """A fake MAIN checkout with an inbox and an outbox holding `notes`."""
    root = tmp_path / "main_tree"
    (root / responder.INBOX_DIRNAME).mkdir(parents=True)
    outbox = root / responder.OUTBOX_DIRNAME
    outbox.mkdir()
    for i, name in enumerate(notes):
        f = outbox / name
        f.write_bytes(b"note\n")
        os.utime(f, (1_000_000 + i, 1_000_000 + i))
    return root


def _map(tmp_path: Path, root: Path | None) -> Path:
    cfg = tmp_path / "ops" / "moon_sync_repos.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    rows = {} if root is None else {"MAIN": str(root)}
    cfg.write_bytes(json.dumps({"channel_codes": rows}).encode("ascii"))
    return cfg


def _state(tmp_path: Path) -> Path:
    return tmp_path / "ops" / "loop" / "control" / "roots_map_probe.json"


def _run(cfg: Path, state: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = probe.main(["--config", str(cfg), "--baseline", str(state)])
    out = capsys.readouterr()
    return rc, out.out + out.err


def _assert_no_identity(text: str, *paths: Path) -> None:
    for p in paths:
        for spelling in {str(p), p.as_posix(), str(p.resolve())}:
            assert spelling not in text, "output names a directory path"
    assert not _ACCOUNT_PATH.search(text), "output carries an account path"
    assert not _EMAIL.search(text), "output carries an email"
    assert "Traceback" not in text


def test_the_identity_detector_fires(tmp_path: Path) -> None:
    """Non-vacuity: the no-path arms below would pass on a blind detector."""
    for leaked in (f"x {tmp_path} y", "\\".join(["C:", "Users", "someone", "x"]), "a@b.example"):
        with pytest.raises(AssertionError):
            _assert_no_identity(leaked, tmp_path)


# ---------------------------------------------------------------- reading


def test_first_reading_reports_outbox_count_newest_and_map_digest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _main_tree(tmp_path, ("old-from-MAIN.txt", "new-from-MAIN.txt"))
    cfg = _map(tmp_path, root)
    rc, text = _run(cfg, _state(tmp_path), capsys)
    assert rc == 0
    assert "outbox_exists=yes" in text
    assert "outbox_entries=2" in text
    assert "newest=new-from-MAIN.txt" in text
    assert f"map_sha256={hashlib.sha256(cfg.read_bytes()).hexdigest()}" in text
    assert "no previous reading" in text


# ------------------------------------------------------------------ drift


def test_drift_is_reported_against_the_previous_reading(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _main_tree(tmp_path)
    cfg = _map(tmp_path, root)
    state = _state(tmp_path)
    _run(cfg, state, capsys)
    # Move the row: a stale or swapped map is exactly what interim d watches.
    other = tmp_path / "other_tree"
    (other / responder.OUTBOX_DIRNAME).mkdir(parents=True)
    cfg.write_bytes(json.dumps({"channel_codes": {"MAIN": str(other)}}).encode("ascii"))
    rc, text = _run(cfg, state, capsys)
    assert rc == 0
    assert "DRIFT map_sha256" in text
    assert "DRIFT outbox_entries 1 -> 0" in text
    assert "DRIFT newest" in text
    _assert_no_identity(text, tmp_path, root, other)


def test_no_drift_when_nothing_moved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Non-vacuity partner of the drift arm: a probe that always cried DRIFT
    would pass the arm above and fail this one."""
    root = _main_tree(tmp_path)
    cfg = _map(tmp_path, root)
    state = _state(tmp_path)
    _run(cfg, state, capsys)
    rc, text = _run(cfg, state, capsys)
    assert rc == 0
    assert "DRIFT" not in text
    assert "no drift since previous reading" in text


def test_a_new_outbox_note_is_drift_in_count_and_newest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _main_tree(tmp_path)
    cfg = _map(tmp_path, root)
    state = _state(tmp_path)
    _run(cfg, state, capsys)
    later = root / responder.OUTBOX_DIRNAME / "b-from-MAIN-RULING.txt"
    later.write_bytes(b"x\n")
    os.utime(later, (2_000_000, 2_000_000))
    _, text = _run(cfg, state, capsys)
    assert "DRIFT outbox_entries 1 -> 2" in text
    assert "DRIFT newest a-from-MAIN-ORDER.txt -> b-from-MAIN-RULING.txt" in text
    assert "DRIFT map_sha256" not in text


# ------------------------------------------------------- write confinement


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_no_write_outside_the_control_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _main_tree(tmp_path)
    cfg = _map(tmp_path, root)
    state = _state(tmp_path)
    before = _snapshot(tmp_path)
    _run(cfg, state, capsys)
    _run(cfg, state, capsys)
    after = _snapshot(tmp_path)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert changed == {"ops/loop/control/roots_map_probe.json"}
    # And the state file holds no path: it lives in a gitignored dir, but the
    # probe's no-path promise covers what it persists too.
    _assert_no_identity(state.read_text(encoding="ascii"), tmp_path, root)


def test_default_state_lives_under_the_control_dir() -> None:
    main = probe.main_checkout(REPO_ROOT)
    assert probe.default_baseline(REPO_ROOT).parent == main / "ops" / "loop" / "control"
    # The map path is the responder's, re-anchored on the MAIN checkout.
    rel = responder.DEFAULT_ROOTS_CONFIG.relative_to(responder.REPO_ROOT)
    assert probe.default_config(REPO_ROOT) == main / rel


# ------------------------------------------- linked worktree (slice N4)


def _git(cwd: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
    )
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True,
        env=env, timeout=60,
    ).stdout


def _repo_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """A tmp main checkout plus a linked worktree of it."""
    main = tmp_path / "checkout"
    main.mkdir()
    _git(main, "init", "-q")
    _git(main, "commit", "-q", "--allow-empty", "-m", "seed")
    wt = tmp_path / "linked"
    _git(main, "worktree", "add", "-q", "--detach", str(wt))
    return main, wt


def test_main_checkout_resolves_a_linked_worktree_to_its_main(tmp_path: Path) -> None:
    main, wt = _repo_with_worktree(tmp_path)
    assert probe.main_checkout(wt) == main.resolve()
    # Non-vacuity: the main checkout answers itself, so the arm above cannot
    # pass on a resolver that returns its argument's parent or a constant.
    assert probe.main_checkout(main) == main.resolve()


def test_main_checkout_outside_git_answers_the_path_itself(tmp_path: Path) -> None:
    plain = tmp_path / "not_a_repo"
    plain.mkdir()
    assert probe.main_checkout(plain) == plain.resolve()


def test_probe_in_a_linked_worktree_reads_the_main_checkouts_map(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The N4 false negative: run from a linked worktree, the probe located the
    map relative to its own file - the worktree, which never holds the
    gitignored map - and printed "map not present". The map lives in the MAIN
    checkout, found through the git common dir."""
    main, wt, target = _worktree_with_map(tmp_path)
    monkeypatch.setattr(probe, "REPO", wt)
    rc = probe.main([])
    out = capsys.readouterr()
    text = out.out + out.err
    assert rc == 0
    assert "map not present" not in text
    assert "outbox_exists=yes" in text
    assert "outbox_entries=1" in text
    assert "fell back" not in text
    # Read-only from a worktree: no baseline is written in either checkout.
    assert not (main / _BASELINE_REL).exists()
    assert not (wt / _BASELINE_REL).exists()
    _assert_no_identity(text, tmp_path, main, wt, target)


_BASELINE_REL = Path("ops") / "loop" / "control" / "roots_map_probe.json"


def _worktree_with_map(tmp_path: Path) -> tuple[Path, Path, Path]:
    main, wt = _repo_with_worktree(tmp_path)
    target = _main_tree(tmp_path)
    rel = responder.DEFAULT_ROOTS_CONFIG.relative_to(responder.REPO_ROOT)
    cfg = main / rel
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_bytes(json.dumps({"channel_codes": {"MAIN": str(target)}}).encode("ascii"))
    assert not (wt / rel).exists()
    return main, wt, target


def test_worktree_run_reports_drift_but_leaves_the_main_baseline_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Merger ruling on N4 refute round 1: drift belongs to the operator's main
    session. A worktree run compares against the MAIN baseline and prints the
    DRIFT, but must not consume it by storing its own reading."""
    main, wt, target = _worktree_with_map(tmp_path)
    # The main checkout's own run still writes its baseline (unchanged path).
    monkeypatch.setattr(probe, "REPO", main)
    assert probe.main([]) == 0
    capsys.readouterr()
    baseline = main / _BASELINE_REL
    assert baseline.is_file()
    os.utime(baseline, (1_500_000, 1_500_000))
    before = (baseline.read_bytes(), baseline.stat().st_mtime_ns)
    later = target / responder.OUTBOX_DIRNAME / "b-from-MAIN-RULING.txt"
    later.write_bytes(b"x\n")
    os.utime(later, (2_000_000, 2_000_000))
    monkeypatch.setattr(probe, "REPO", wt)
    for _ in range(2):  # twice: the second run must STILL see the drift
        assert probe.main([]) == 0
        out = capsys.readouterr()
        assert "DRIFT outbox_entries 1 -> 2" in out.out
        assert (baseline.read_bytes(), baseline.stat().st_mtime_ns) == before
        assert not (wt / _BASELINE_REL).exists()
        _assert_no_identity(out.out + out.err, tmp_path, main, wt, target)


def test_worktree_run_with_no_main_baseline_never_claims_to_store_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Session 74 residue N5(a): a linked-worktree run with no main baseline
    printed "this one is stored as the baseline" and then "read-only, baseline
    not updated" - a contradiction. A read-only run must never claim storage."""
    main, wt, target = _worktree_with_map(tmp_path)
    monkeypatch.setattr(probe, "REPO", wt)
    assert probe.main([]) == 0
    out = capsys.readouterr().out
    assert "stored as the baseline" not in out
    assert "no previous reading" in out
    assert "read-only, baseline not updated" in out
    assert not (main / _BASELINE_REL).exists()
    assert not (wt / _BASELINE_REL).exists()
    # Non-vacuity: the main checkout's own first run still says it stores.
    monkeypatch.setattr(probe, "REPO", main)
    assert probe.main([]) == 0
    out = capsys.readouterr().out
    assert "stored as the baseline" in out
    assert "read-only" not in out
    assert (main / _BASELINE_REL).is_file()
    _assert_no_identity(out, tmp_path, main, wt, target)


@pytest.mark.parametrize("failure", ["returns_false", "raises_oserror"])
def test_failed_baseline_write_never_claims_storage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """Sibling of N5(a): a first run whose baseline write fails printed "this
    one is stored as the baseline" and then "could not be stored". The stored
    claim may appear only after a successful write. `atomic_write_json`
    reports failure by returning False; a raised OSError is covered too."""
    cfg = _map(tmp_path, _main_tree(tmp_path))
    state = _state(tmp_path)

    def _fail(*_a: object, **_k: object) -> bool:
        if failure == "raises_oserror":
            raise OSError("simulated write failure")
        return False

    monkeypatch.setattr(probe._atomic, "atomic_write_json", _fail)
    rc, text = _run(cfg, state, capsys)
    assert rc == 0
    assert "stored as the baseline" not in text
    assert "could not be stored" in text
    assert "no previous reading" in text
    assert not state.exists()
    _assert_no_identity(text, tmp_path, cfg, state)
    # Non-vacuity: with the real writer the same first run claims storage.
    monkeypatch.undo()
    rc, text = _run(cfg, state, capsys)
    assert rc == 0
    assert "stored as the baseline" in text
    assert "could not be stored" not in text
    assert state.is_file()


_RAW_SENTINEL = "raw-detail-sentinel-n7c"


def _non_oserror(kind: str) -> Exception:
    if kind == "value":
        return ValueError(_RAW_SENTINEL)
    if kind == "unicode":
        return UnicodeEncodeError("ascii", _RAW_SENTINEL, 0, 1, _RAW_SENTINEL)
    return RuntimeError(_RAW_SENTINEL)


@pytest.mark.parametrize("kind", ["value", "unicode", "runtime"])
def test_non_oserror_during_baseline_write_degrades_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Session 75 residue N7c: only OSError was caught around the baseline
    write, so a ValueError or UnicodeEncodeError from the writer escaped as a
    raw traceback. It must degrade exactly like the OSError path: the
    friendly "could not be stored" line, no storage claim, exit 0 (the
    module's recorded reporter idiom), and the raw error goes to the log file
    only, never to the console."""
    cfg = _map(tmp_path, _main_tree(tmp_path))
    state = _state(tmp_path)
    logged: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            logged.append(record.getMessage())

    def _boom(*_a: object, **_k: object) -> bool:
        raise _non_oserror(kind)

    monkeypatch.setattr(probe._atomic, "atomic_write_json", _boom)
    monkeypatch.setattr(probe, "_file_handlers", lambda: [_Capture()], raising=False)
    rc, text = _run(cfg, state, capsys)
    assert rc == 0
    assert "Traceback" not in text
    assert _RAW_SENTINEL not in text, "raw error string reached the console"
    assert "could not be stored" in text
    assert "stored as the baseline" not in text
    assert not state.exists()
    _assert_no_identity(text, tmp_path, cfg, state)
    assert len(logged) == 1 and _RAW_SENTINEL in logged[0], "raw error was not logged"


def test_baseline_write_never_swallows_keyboard_interrupt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The N7c catch is `Exception`, never BaseException: Ctrl-C still stops it."""
    cfg = _map(tmp_path, _main_tree(tmp_path))

    def _interrupt(*_a: object, **_k: object) -> bool:
        raise KeyboardInterrupt

    monkeypatch.setattr(probe._atomic, "atomic_write_json", _interrupt)
    with pytest.raises(KeyboardInterrupt):
        probe.main(["--config", str(cfg), "--baseline", str(_state(tmp_path))])


def test_deeply_nested_baseline_is_no_baseline_not_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N7c refute sibling 1: `_load_previous` caught only (OSError,
    ValueError); a deeply nested baseline raised RecursionError out of main."""
    cfg = _map(tmp_path, _main_tree(tmp_path))
    state = _state(tmp_path)
    state.parent.mkdir(parents=True, exist_ok=True)
    # A 3-byte stand-in: the real trigger depth is interpreter-specific
    # (about 1001 on 3.11, about 20000 on 3.14), so the parse of exactly
    # these bytes raises RecursionError and every other parse is untouched.
    poison = "[[["
    state.write_bytes(poison.encode("ascii"))
    real_loads = json.loads

    def _deep(text: str, *a: object, **k: object) -> object:
        if text == poison:
            raise RecursionError("maximum recursion depth exceeded")
        return real_loads(text, *a, **k)

    monkeypatch.setattr(probe.json, "loads", _deep)
    logged: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            logged.append(record.getMessage())

    monkeypatch.setattr(probe, "_file_handlers", lambda: [_Capture()], raising=False)
    rc, text = _run(cfg, state, capsys)
    assert rc == 0
    assert "Traceback" not in text
    assert "no previous reading" in text
    _assert_no_identity(text, tmp_path, cfg, state)
    assert len(logged) == 1 and "RecursionError" in logged[0]
    # The run replaced the poisoned baseline with a good one.
    assert probe._load_previous(state) is not None


def test_common_dir_decode_failure_falls_back(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """N7c refute sibling 2: a UnicodeDecodeError out of the git call (a
    non-UTF-8 locale) escaped `_resolve_main`. It must mean "not resolved"."""

    def _undecodable(*_a: object, **_k: object) -> object:
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr(probe.subprocess, "run", _undecodable)
    monkeypatch.setattr(probe, "_file_handlers", lambda: [], raising=False)
    assert probe._resolve_main(tmp_path) is None
    cfg = _map(tmp_path, _main_tree(tmp_path))
    rc, text = _run(cfg, _state(tmp_path), capsys)
    assert rc == 0
    assert "fell back" in text
    assert "Traceback" not in text


def test_common_dir_git_output_is_decoded_leniently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The git output is decoded as UTF-8 with replacement, never by locale."""
    seen: dict[str, object] = {}

    def _fake(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 1, "", "")

    monkeypatch.setattr(probe.subprocess, "run", _fake)
    assert probe._resolve_main(tmp_path) is None
    assert seen.get("encoding") == "utf-8"
    assert seen.get("errors") == "replace"


def test_tampered_baseline_values_print_ascii_and_no_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """N7c sweep sibling 3: DRIFT lines printed the PREVIOUS reading's values
    raw. A non-ASCII value raises UnicodeEncodeError on a cp1252 console and a
    path-shaped value leaks identity. Previous values render as safe or
    `(withheld)`."""
    cfg = _map(tmp_path, _main_tree(tmp_path))
    state = _state(tmp_path)
    state.parent.mkdir(parents=True, exist_ok=True)
    leak = str(tmp_path / "leaked")
    prior = {"map_present": True, "main_row": True, "outbox_exists": True,
             "outbox_entries": [1, 2], "newest": "snow\u2603man", "map_sha256": leak}
    state.write_bytes(json.dumps({"schema": 1, "reading": prior}).encode("ascii"))
    rc, text = _run(cfg, state, capsys)
    assert rc == 0
    assert text.isascii(), "a DRIFT line carries a non-ASCII byte"
    assert leak not in text
    _assert_no_identity(text, tmp_path, cfg, state)
    # Non-vacuity: the drift itself is still reported, values withheld.
    assert "DRIFT newest (withheld) -> a-from-MAIN-ORDER.txt" in text
    assert "DRIFT outbox_entries (withheld) -> 1" in text


def test_file_handlers_are_file_only() -> None:
    """The raw-error sink must never include a console stream handler."""
    handlers = probe._file_handlers()
    assert handlers, "no file handler: the raw error would be logged nowhere"
    assert all(isinstance(h, logging.FileHandler) for h in handlers)
    # Non-vacuity: the logger DOES carry a console handler that was filtered out.
    every = probe._log_setup.get_logger(probe.__name__).handlers
    assert any(not isinstance(h, logging.FileHandler) for h in every)


def test_failed_common_dir_resolution_says_it_fell_back(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """E.g. git < 2.31 rejects --path-format: one stderr line, no path."""
    plain = tmp_path / "not_a_repo"
    plain.mkdir()
    root = _main_tree(tmp_path)
    cfg = _map(tmp_path, root)
    monkeypatch.setattr(probe, "REPO", plain)
    assert probe.main(["--config", str(cfg), "--baseline", str(_state(tmp_path))]) == 0
    out = capsys.readouterr()
    fell = [ln for ln in out.err.splitlines() if "fell back" in ln]
    assert len(fell) == 1
    assert "outbox_exists=yes" in out.out
    _assert_no_identity(out.out + out.err, tmp_path, plain, root)


# --------------------------------------------------------------- degrade


@pytest.mark.parametrize(
    ("setup", "expected"),
    [
        ("missing", "map not present"),
        ("garbage", "map not readable"),
        ("no_main_row", "no MAIN row"),
        ("no_outbox", "outbox_exists=no"),
    ],
)
def test_degraded_maps_give_one_friendly_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], setup: str, expected: str
) -> None:
    cfg = tmp_path / "ops" / "moon_sync_repos.json"
    if setup == "garbage":
        cfg.parent.mkdir(parents=True)
        cfg.write_bytes(b"{not json")
    elif setup == "no_main_row":
        _map(tmp_path, None)
    elif setup == "no_outbox":
        _map(tmp_path, tmp_path / "nowhere")
    rc, text = _run(cfg, _state(tmp_path), capsys)
    assert rc == 0
    assert expected in text
    _assert_no_identity(text, tmp_path, cfg)


def test_invalid_args_exit_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        probe.main(["--no-such-flag"])
    assert exc.value.code == 2
    capsys.readouterr()


def test_unsafe_newest_filename_is_withheld(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _main_tree(tmp_path, ("someone@example.com.txt",))
    cfg = _map(tmp_path, root)
    _, text = _run(cfg, _state(tmp_path), capsys)
    assert "newest=(withheld)" in text
    _assert_no_identity(text, tmp_path, root)


def test_command_line_runs_from_another_directory(tmp_path: Path) -> None:
    """The real entry point, launched by sys.executable from outside the repo."""
    root = _main_tree(tmp_path)
    cfg = _map(tmp_path, root)
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "roots_map_probe.py"),
         "--config", str(cfg), "--baseline", str(_state(tmp_path))],
        cwd=tmp_path, capture_output=True, text=True, timeout=120, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "outbox_exists=yes" in proc.stdout
    _assert_no_identity(proc.stdout + proc.stderr, tmp_path, root)


def test_trailing_newline_name_is_withheld_and_drift_stays_one_line() -> None:
    """Refute round 2: `$` matches before a final newline, so `abc\n` passed
    the safe-name pattern and split a DRIFT line in two. The whole name must
    match; a newline-bearing value is withheld."""
    assert probe._show("abc\n") == "(withheld)"
    assert probe._safe_name("abc\n") == "(withheld)"
    lines = probe.compare({"newest": "abc\n"}, {"newest": "b"})
    assert lines, "compare emitted nothing"
    assert all("\n" not in ln for ln in lines)
    assert any("DRIFT newest (withheld) -> b" in ln for ln in lines)
    # Non-vacuity: a legitimate neighbour still prints.
    assert probe._show("abc") == "abc"
    assert probe._show("a-from-MAIN-ORDER.txt") == "a-from-MAIN-ORDER.txt"
