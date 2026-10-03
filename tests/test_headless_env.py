"""The headless-route gate: every unattended `claude` spawn goes through a proxy.

OPERATOR DIRECTIVE, 2026-10-02. Every headless Claude run this tree starts runs
on a SECOND subscription through a local proxy. The proxy's base URL is read at
spawn time from the USER environment store (HKCU\\Environment) under
`CLAUDE_HEADLESS_BASE_URL`, falling back to the process environment, and is
handed to the CHILD only as `ANTHROPIC_BASE_URL`. FAIL CLOSED: unset, malformed
or unreachable means no spawn, and there is no fallback route.

Deleting the variable is the operator's kill switch for every tree at once. So
when the user store CAN be read and the value is ABSENT, a stale copy in this
process's inherited environment does not resurrect it - that is the arm
`test_the_kill_switch_beats_a_stale_process_copy`.

No arm here names the operator's real endpoint. Every reachable endpoint is an
ephemeral listener this file opens itself, so the test cannot pass by accident
on a host where the real proxy happens to be running.
"""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

from core import headless_env as he

NAME = he.ENV_HEADLESS_BASE_URL
ROOT = Path(__file__).resolve().parents[1]
RESPONDER_PATH = ROOT / "tools" / "moon_sync_responder.py"


@pytest.fixture()
def listener():
    """A real TCP listener on an ephemeral loopback port; yields its URL."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(4)
    port = srv.getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        srv.close()


@pytest.fixture()
def closed_url():
    """A loopback URL whose port was just released, so a connect is refused."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{port}"


def _store(value):
    """A user-store reader that answers `value` (None means ABSENT)."""

    def read(name):
        assert name == NAME
        return value

    return read


def _unavailable(name):
    raise he.StoreUnavailable("no user store on this platform")


def test_the_variable_names_are_the_directive_names():
    assert he.ENV_HEADLESS_BASE_URL == "CLAUDE_HEADLESS_BASE_URL"
    assert he.ENV_CHILD_BASE_URL == "ANTHROPIC_BASE_URL"


def test_unset_everywhere_refuses_and_builds_no_env():
    decision = he.prepare_headless_env(read_store=_store(None), environ={})
    assert decision.ok is False
    assert decision.env is None
    assert decision.reason == he.REFUSE_UNSET


def test_empty_value_refuses():
    decision = he.prepare_headless_env(read_store=_store("   "), environ={})
    assert decision.ok is False
    assert decision.reason == he.REFUSE_UNSET


def test_a_closed_port_refuses(closed_url):
    decision = he.prepare_headless_env(
        read_store=_store(closed_url), environ={}, timeout=0.5
    )
    assert decision.ok is False
    assert decision.env is None
    assert decision.reason == he.REFUSE_UNREACHABLE


def test_a_malformed_value_refuses_without_probing():
    def never(*a, **k):  # pragma: no cover - reaching this is the failure
        raise AssertionError("a malformed URL must not be probed")

    for bad in ("not a url", "ftp://127.0.0.1:1", "http://", "http://127.0.0.1:notaport"):
        decision = he.prepare_headless_env(read_store=_store(bad), environ={}, connect=never)
        assert decision.ok is False, bad
        assert decision.reason == he.REFUSE_MALFORMED, bad


def test_the_happy_path_sets_the_child_var_and_leaves_the_parent_alone(listener):
    parent = dict(os.environ)
    decision = he.prepare_headless_env(read_store=_store(listener))
    assert decision.ok is True, decision.reason
    assert decision.env is not None
    assert decision.env[he.ENV_CHILD_BASE_URL] == listener
    # The child is a COPY of the parent plus the one key.
    copied = all(
        decision.env.get(k) == v
        for k, v in parent.items()
        if not he._stripped(k)
    )
    assert copied, "the child env is not a copy of the parent"
    unchanged = dict(os.environ) == parent
    assert unchanged, "the parent environment was mutated"
    distinct = decision.env is not os.environ
    assert distinct, "the child env IS the parent env"


def test_the_parent_keeps_a_different_base_url_untouched(listener, monkeypatch):
    """A parent that already carries ANTHROPIC_BASE_URL keeps its own value."""
    monkeypatch.setenv(he.ENV_CHILD_BASE_URL, "http://parent.invalid:1")
    decision = he.prepare_headless_env(read_store=_store(listener))
    assert decision.ok is True, decision.reason
    assert decision.env[he.ENV_CHILD_BASE_URL] == listener
    kept = os.environ.get(he.ENV_CHILD_BASE_URL) == "http://parent.invalid:1"
    assert kept, "the parent's own ANTHROPIC_BASE_URL was overwritten"


STRIPPED = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_BEDROCK_BASE_URL",
    "ANTHROPIC_VERTEX_BASE_URL",
    "ANTHROPIC_VERTEX_PROJECT_ID",
)


def test_auth_and_routing_vars_never_reach_the_child(listener, monkeypatch):
    """A billing bypass: an inherited key or provider switch outranks the proxy."""
    for name in STRIPPED:
        monkeypatch.setenv(name, "inherited-" + name.lower())
    parent = dict(os.environ)
    decision = he.prepare_headless_env(read_store=_store(listener))
    assert decision.ok is True, decision.reason
    leaked = sorted(n for n in STRIPPED if n in decision.env)
    assert leaked == [], f"inherited into the child: {leaked}"
    unchanged = dict(os.environ) == parent
    assert unchanged, "stripping the child mutated the parent environment"
    kept = all(os.environ.get(n) == "inherited-" + n.lower() for n in STRIPPED)
    assert kept, "the parent lost a variable the child was stripped of"


def test_r6_every_anthropic_and_claude_code_key_is_dropped_by_prefix(listener):
    parent = {
        "PATH": "p",
        "CLAUDE_CODE_MESSAGING_SOCKET": "s",
        "CLAUDECODE": "1",
        "CLAUDE_CODE_ENTRYPOINT": "cli",
        "ANTHROPIC_MODEL": "m",
        "ANTHROPIC_BASE_URL": "http://parent.invalid:1",
        "CLAUDE_CODE_GIT_BASH_PATH": "bash.exe",
        "CLAUDE_HEADLESS_BASE_URL": "kept-not-a-prefix",
    }
    decision = he.prepare_headless_env(read_store=_store(listener), environ=parent)
    assert decision.ok is True, decision.reason
    got = sorted(decision.env)
    assert got == sorted(
        ["PATH", "CLAUDE_CODE_GIT_BASH_PATH", "CLAUDE_HEADLESS_BASE_URL", "ANTHROPIC_BASE_URL"]
    ), got
    assert decision.env["ANTHROPIC_BASE_URL"] == listener
    assert decision.env["CLAUDE_CODE_GIT_BASH_PATH"] == "bash.exe"
    assert parent["CLAUDECODE"] == "1", "the parent mapping was mutated"


@pytest.mark.skipif(os.name != "nt", reason="Windows environment keys are case-insensitive")
def test_r6_the_prefix_match_is_case_insensitive_on_windows(listener):
    parent = {"anthropic_api_key": "k", "Claude_Code_Oauth_Token": "t", "PATH": "p"}
    decision = he.prepare_headless_env(read_store=_store(listener), environ=parent)
    assert sorted(decision.env) == ["ANTHROPIC_BASE_URL", "PATH"], sorted(decision.env)


def test_the_strip_list_is_one_named_tuple():
    assert set(STRIPPED) <= set(he.CHILD_ENV_STRIPPED)
    assert isinstance(he.CHILD_ENV_STRIPPED, tuple)
    assert he.ENV_CHILD_BASE_URL not in he.CHILD_ENV_STRIPPED
    uncovered = [n for n in he.CHILD_ENV_STRIPPED if not he._stripped(n)]
    assert uncovered == [], f"named but not covered by the prefix strip: {uncovered}"
    # Non-vacuity: an unrelated key survives the same predicate.
    assert not he._stripped("PATH")


def test_the_user_store_wins_over_the_process_env(listener, closed_url):
    decision = he.prepare_headless_env(
        read_store=_store(listener), environ={NAME: closed_url}, timeout=0.5
    )
    assert decision.ok is True, decision.reason
    assert decision.env[he.ENV_CHILD_BASE_URL] == listener


def test_the_process_env_is_the_fallback_when_the_store_cannot_be_read(listener):
    decision = he.prepare_headless_env(read_store=_unavailable, environ={NAME: listener})
    assert decision.ok is True, decision.reason
    assert decision.env[he.ENV_CHILD_BASE_URL] == listener


def test_the_kill_switch_beats_a_stale_process_copy(listener):
    """Deleted from the user store, still inherited here: REFUSE.

    A process started before the operator deleted the variable still carries
    it. Honouring that copy would make the kill switch take effect only after
    every long-lived process had restarted, which is not a kill switch.
    """
    decision = he.prepare_headless_env(read_store=_store(None), environ={NAME: listener})
    assert decision.ok is False
    assert decision.reason == he.REFUSE_UNSET


def test_the_probe_target_is_derived_from_the_value(listener):
    seen = []

    def connect(address, timeout):
        seen.append(address)

        class _C:
            def close(self):
                pass

        return _C()

    url = "http://example.invalid:4711/some/path"
    decision = he.prepare_headless_env(read_store=_store(url), environ={}, connect=connect)
    assert decision.ok is True
    assert seen == [("example.invalid", 4711)]
    https = he.prepare_headless_env(
        read_store=_store("https://example.invalid"), environ={}, connect=connect
    )
    assert https.ok is True
    assert seen[-1] == ("example.invalid", 443)


def test_a_refusal_is_logged(caplog):
    with caplog.at_level("WARNING"):
        he.prepare_headless_env(read_store=_store(None), environ={})
    assert any(he.REFUSE_UNSET in r.getMessage() for r in caplog.records)


def test_reasons_never_carry_the_value(closed_url):
    """A refusal reason reaches held files and logs; the URL must not."""
    decision = he.prepare_headless_env(read_store=_store(closed_url), environ={}, timeout=0.5)
    assert closed_url not in decision.reason
    assert closed_url.rsplit(":", 1)[1] not in decision.reason


def test_the_default_reader_off_windows_is_unavailable(monkeypatch):
    monkeypatch.setattr(he.os, "name", "posix")
    with pytest.raises(he.StoreUnavailable):
        he.read_user_store(NAME)


@pytest.mark.skipif(os.name != "nt", reason="the user environment store is a Windows registry key")
def test_the_default_reader_answers_absent_for_an_unset_name():
    """Non-vacuity for the real winreg path: an absent name reads as None."""
    assert he.read_user_store("RESINCOMPUTE_SURELY_UNSET_" + "X" * 8) is None


def test_no_tracked_code_hardcodes_the_proxy_port():
    """The probe target comes from the variable, never from a literal."""
    src = Path(he.__file__).read_text(encoding="ascii")
    port = str(3000 + 456)
    assert port not in src
    # Non-vacuity: the same check fires on a line that does carry it.
    assert port in f"http://127.0.0.1:{port}"


# ---------------------------------------------------------------------------
# The responder's one `claude` spawn routes through the helper above. These
# arms drive `_spawn_headless` and `run_once` with `subprocess.run` and
# `shutil.which` intercepted, so nothing here launches a session. The module is
# loaded by importlib and its source is never read - a source reader is a
# shape grader, see `tools/gate_mutation_runner.SHAPE_GRADER_MODULES`.
# ---------------------------------------------------------------------------


@pytest.fixture()
def rsp(tmp_path):
    """The responder with every `DEFAULT_*` path redirected into `tmp_path`."""
    spec = importlib.util.spec_from_file_location(
        "responder_headless_route_under_test", RESPONDER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


class _Run:
    """A `subprocess.run` stand-in that records and answers a fixed result."""

    def __init__(self, stdout="ok", stderr="", returncode=0):
        self.calls = 0
        self.kwargs: dict = {}
        self._out = (stdout, stderr, returncode)

    def __call__(self, *args, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        out, err, rc = self._out
        return subprocess.CompletedProcess(args=args[0], returncode=rc, stdout=out, stderr=err)


def _refusing():
    return he.Decision(False, None, he.REFUSE_UNSET)


def _routing():
    return he.Decision(True, {"PATH": "x", he.ENV_CHILD_BASE_URL: "http://proxy.invalid:9"}, "")


@pytest.fixture()
def which(monkeypatch):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _n: str(ROOT / "fake-claude-shim.cmd"))


@pytest.fixture()
def trusted(rsp, monkeypatch):
    monkeypatch.setattr(rsp, "workspace_trust", lambda *_a, **_k: (True, "trusted"))


def test_the_responder_gate_is_the_real_helper_by_default(rsp):
    assert rsp._headless_gate is he.prepare_headless_env


def test_a_refused_route_spawns_nothing(rsp, monkeypatch, which):
    run = _Run()
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(rsp, "_headless_gate", _refusing)
    with pytest.raises(rsp.HeadlessRefused) as info:
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert run.calls == 0, "the session was spawned although the route refused"
    assert str(info.value) == he.REFUSE_UNSET
    assert isinstance(info.value, rsp.SpawnFailed)


def test_a_routed_spawn_carries_the_child_env(rsp, monkeypatch, which):
    run = _Run()
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(rsp, "_headless_gate", _routing)
    assert rsp._spawn_headless("a prompt", rsp.Bounds()) == "ok"
    assert run.calls == 1
    got = run.kwargs.get("env", {}).get(he.ENV_CHILD_BASE_URL)
    assert got == "http://proxy.invalid:9", "the spawn did not carry the routed env"


def test_the_kill_switch_end_to_end_through_the_responder(rsp, monkeypatch, which):
    """The REAL helper, with the user store answering ABSENT: no spawn."""
    run = _Run()
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(
        rsp, "_headless_gate",
        lambda: he.prepare_headless_env(read_store=lambda _n: None, environ={}),
    )
    with pytest.raises(rsp.HeadlessRefused):
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert run.calls == 0


def test_a_usage_limit_exit_raises_usage_limited_and_is_not_retried(rsp, monkeypatch, which):
    run = _Run(stdout="Claude AI usage limit reached|1900000000", returncode=1)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(rsp, "_headless_gate", _routing)
    with pytest.raises(rsp.UsageLimited) as info:
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert info.value.reset_at == 1900000000.0
    assert run.calls == 1, "a usage limit must not be retried inside the cycle"


def test_a_usage_limit_on_stderr_is_detected(rsp, monkeypatch, which):
    run = _Run(stdout="", stderr="API Error: 429 rate_limit_error", returncode=1)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(rsp, "_headless_gate", _routing)
    with pytest.raises(rsp.UsageLimited):
        rsp._spawn_headless("a prompt", rsp.Bounds())


def test_a_draft_without_any_limit_phrase_is_a_draft(rsp, monkeypatch, which):
    """Survival guard. RULED 2026-10-02: a limit phrase ANYWHERE backs off, even
    in a real draft, because a false positive only backs off. So the neighbour
    that must survive is a draft carrying no limit phrase at all."""
    text = rsp.RESPONDER_TAG + "\nThe hop budget held at eight.\n" + "x" * 400
    run = _Run(stdout=text, returncode=0)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(rsp, "_headless_gate", _routing)
    assert rsp._spawn_headless("a prompt", rsp.Bounds()) == text


def _armed_cycle(rsp, tmp_path, spawn=None):
    from tests.test_moon_sync_responder import _agree, _note

    _agree(rsp)
    inbox = tmp_path / "inbox"
    if not inbox.is_dir():
        _note(inbox, "2026-09-07-1900-from-RC-question.md")
    (tmp_path / "rc" / "moon_sync_inbox").mkdir(parents=True, exist_ok=True)
    return rsp.run_once(
        inbox=inbox,
        roots={"RC": tmp_path / "rc"},
        bounds=rsp.Bounds(armed=True),
        spawn=spawn,
    )


def test_a_usage_limit_backs_off_and_the_next_cycle_spawns_nothing(
    rsp, tmp_path, monkeypatch, which, trusted
):
    run = _Run(stdout="Claude AI usage limit reached", returncode=1)
    monkeypatch.setattr(subprocess, "run", run)
    gate_calls = []

    def gate():
        gate_calls.append(1)
        return _routing()

    monkeypatch.setattr(rsp, "_headless_gate", gate)

    first = _armed_cycle(rsp, tmp_path)
    assert first["termination"] == "usage-limited", first
    until = json.loads(rsp.DEFAULT_BACKOFF.read_text(encoding="ascii"))["until"]
    assert until > time.time()

    second = _armed_cycle(rsp, tmp_path)
    assert second["termination"] == "usage-backoff", second
    assert run.calls == 1, "the backoff did not stop the second spawn"
    assert len(gate_calls) == 1, "a backed-off cycle still probed a route"
    for name in ("usage-limited", "usage-backoff", "headless-refused"):
        assert name in rsp.TERMINATIONS, name


def test_the_backoff_expires(rsp, tmp_path, monkeypatch, which, trusted):
    run = _Run(stdout="Claude AI usage limit reached", returncode=1)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(rsp, "_headless_gate", _routing)
    _armed_cycle(rsp, tmp_path)
    # Rewind the recorded backoff instead of moving the clock.
    rsp.DEFAULT_BACKOFF.write_bytes(json.dumps({"until": time.time() - 1}).encode("ascii"))
    again = _armed_cycle(rsp, tmp_path)
    assert again["termination"] == "usage-limited", again
    assert run.calls == 2


def test_a_reset_stamp_sets_the_backoff_and_is_clamped(rsp):
    now = 1_000_000.0
    assert rsp.record_backoff(rsp.DEFAULT_BACKOFF, now + 120, now)
    assert json.loads(rsp.DEFAULT_BACKOFF.read_text(encoding="ascii"))["until"] == now + 120
    assert rsp.record_backoff(rsp.DEFAULT_BACKOFF, now + 10 * 86400, now)
    clamped = json.loads(rsp.DEFAULT_BACKOFF.read_text(encoding="ascii"))["until"]
    assert clamped == now + rsp.USAGE_BACKOFF_SECONDS


def test_a_refused_route_is_its_own_termination_and_holds_nothing(
    rsp, tmp_path, monkeypatch, which, trusted
):
    run = _Run()
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(
        rsp, "_headless_gate", lambda: he.Decision(False, None, he.REFUSE_UNREACHABLE)
    )
    result = _armed_cycle(rsp, tmp_path)
    assert result["termination"] == "headless-refused", result
    assert result["reasons"] == [he.REFUSE_UNREACHABLE]
    assert run.calls == 0
    assert not list(rsp.DEFAULT_STAGING.glob("held/*"))


def test_a_plain_spawn_failure_still_reads_spawn_failed(rsp, tmp_path, trusted):
    """Survival guard: the new handlers did not swallow the old one."""

    def broken(prompt, bounds):
        raise rsp.SpawnFailed("FileNotFoundError")

    assert _armed_cycle(rsp, tmp_path, spawn=broken)["termination"] == "spawn-failed"
