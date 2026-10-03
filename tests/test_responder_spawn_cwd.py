"""The workspace-trust check and the headless spawn share ONE cwd: `SPAWN_CWD`.

WHY THIS MODULE EXISTS. `tools/moon_sync_responder.py` checks
`workspace_trust(<cwd>)` in `run_once` and later spawns the headless session
with `subprocess.run(..., cwd=<cwd>)` in `_spawn_headless`. Those were two
separate spellings of the repo root. If they drift apart, the trust gate
certifies one directory and the session runs in another - the exact silent
permission drop the trust gate exists to prevent. So both sites must read the
single module-level `SPAWN_CWD`, and this module proves it BEHAVIOURALLY: it
rebinds `SPAWN_CWD` to a sentinel that is NOT the repo root, drives each site
through its real code path with the callable at that site replaced by a
recorder, and asserts the recorder saw the sentinel. A site still reading
`REPO_ROOT` (or any other spelling) records the repo root and goes red.

A grep for the identifier would pass against a module that names the constant
in a comment and spawns somewhere else; that is why no arm here reads source.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"


@pytest.fixture()
def rsp(tmp_path):
    """The responder with every `DEFAULT_` Path redirected into `tmp_path`.

    Same discovered-redirection shape as `test_responder_refusal_gates.py`, so
    no arm here can read or write the operator's live runtime state.
    """
    spec = importlib.util.spec_from_file_location("moon_sync_responder_spawn_cwd", MODULE)
    assert spec is not None and spec.loader is not None, f"cannot load {MODULE}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


@pytest.fixture()
def sentinel(rsp, tmp_path, monkeypatch):
    """Rebind `SPAWN_CWD` to a directory that is provably NOT the repo root.

    `raising=True` is monkeypatch's default, so against a module with no
    `SPAWN_CWD` attribute this fixture itself fails - the red at HEAD.
    """
    target = tmp_path / "spawn-cwd-sentinel"
    target.mkdir()
    # NON-VACUITY: if the sentinel equalled the repo root, a site still
    # reading `REPO_ROOT` would record the same value and every arm would pass.
    assert target.resolve() != Path(rsp.REPO_ROOT).resolve()
    monkeypatch.setattr(rsp, "SPAWN_CWD", target)
    return target


def test_spawn_cwd_defaults_to_the_repo_root(rsp):
    """The adjudicated call: KEEP the repo as the child's cwd.

    The child's allowed tools (Read, Grep, git log, pytest) resolve against it.
    """
    assert isinstance(rsp.SPAWN_CWD, Path)
    assert rsp.SPAWN_CWD == rsp.REPO_ROOT


def test_the_trust_check_is_handed_spawn_cwd(rsp, sentinel, tmp_path, monkeypatch):
    """Drive `run_once` to `GATE:workspace-trust` and record what it checks."""
    seen: list[Path] = []

    def recorder(cwd, *_a, **_k):
        seen.append(cwd)
        return False, "UNTRUSTED (recorded by the spawn-cwd test)"

    monkeypatch.setattr(rsp, "workspace_trust", recorder)

    rsp.DEFAULT_CONFIRMATION.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_CONFIRMATION.write_text(
        json.dumps({"confirmed_by": "RC", "note": "agreed.md", "expires": 9_999_999_999})
    )
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "2026-09-08-1900-from-RC-question.md").write_bytes(b"please measure\n")
    (tmp_path / "rc" / "moon_sync_inbox").mkdir(parents=True)

    spawned: list[str] = []
    result = rsp.run_once(
        inbox=inbox,
        roots={"RC": tmp_path / "rc"},
        bounds=rsp.Bounds(armed=True),
        spawn=lambda prompt, _b: spawned.append(prompt) or "",
        now=30_000.0,
    )

    assert result["termination"] == "untrusted-workspace", result
    assert spawned == [], "the recorder refused, yet a session was started"
    assert len(seen) == 1, f"the trust check ran {len(seen)} time(s), so this arm observed nothing"
    assert Path(seen[0]) == sentinel, (
        f"the trust check was handed {seen[0]!r}, not SPAWN_CWD {sentinel!r}"
    )


def test_the_subprocess_spawn_is_handed_spawn_cwd(rsp, sentinel, monkeypatch, tmp_path):
    """Drive `_spawn_headless` to `subprocess.run` and record its `cwd`.

    The fleet kit hands its OWN root to `run` as `cwd`; the responder's `run=`
    wrapper must replace it with `SPAWN_CWD`. `kit_route` puts the kit's root
    at a third directory, so a wrapper that passed the kit's cwd through would
    record that and go red here.
    """
    import json

    from tests.test_headless_env import kit_route

    calls: list[dict] = []

    def run(*args, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout=json.dumps({"result": "ok"}), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", run)
    kit_route(rsp, monkeypatch, tmp_path)
    assert Path(rsp.KIT_ROOT).resolve() != sentinel.resolve(), "non-vacuity: the roots must differ"

    assert rsp._spawn_headless("a prompt", rsp.Bounds()) == "ok"

    assert len(calls) == 1, f"subprocess.run ran {len(calls)} time(s), so this arm observed nothing"
    assert "cwd" in calls[0], "the spawn passed no cwd at all"
    assert Path(calls[0]["cwd"]) == sentinel, (
        f"the spawn ran in {calls[0]['cwd']!r}, not SPAWN_CWD {sentinel!r}"
    )
