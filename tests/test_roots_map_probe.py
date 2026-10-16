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
