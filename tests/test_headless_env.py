"""The headless route: every unattended `claude` spawn goes through a proxy.

OPERATOR DIRECTIVE, 2026-10-02. Every headless Claude run this tree starts runs
on a SECOND subscription through a local proxy, read at spawn time from the
USER environment store under `CLAUDE_HEADLESS_BASE_URL`. FAIL CLOSED: unset,
malformed, non-loopback or unreachable means no spawn, and there is no
fallback route.

SINCE FLEET-KIT v3 THE ROUTE IS THE KIT'S (`ops/fleet_kit/fleet_headless.py`),
and the responder's spawn goes through `fleet_headless.spawn`. This tree's own
URL reader and probe were deleted; what `core.headless_env` keeps is the
prefix strip applied ON TOP of the kit's child env. So this file has two
halves: the strip, and the responder's spawn driven end to end through the
kit.

HOW THE ROUTE IS DRIVEN WITHOUT BYPASSING IT. The URL is injected through the
kit's own `base_url(registry=..., environ=...)` and the socket through the
kit's own `connect=`; the kit's `check_url` and `probe` always run. The kit's
root is a tmp directory. `subprocess.run` is replaced, so no arm launches a
session. No arm names the operator's real endpoint.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

from core import headless_env as he
from ops.fleet_kit import fleet_headless as kit

ROOT = Path(__file__).resolve().parents[1]
RESPONDER_PATH = ROOT / "tools" / "moon_sync_responder.py"


#: A loopback URL. No socket is ever opened against it: `connect` is injected.
STUB_URL = "http://127.0.0.1:9"


class _Conn:
    def close(self) -> None:
        pass


class Dialer:
    """A `socket.create_connection` stand-in that records every dial."""

    def __init__(self, accept: bool = True) -> None:
        self.accept = accept
        self.dialled: list[tuple[str, int]] = []

    def __call__(self, address, timeout=None):
        self.dialled.append(address)
        if not self.accept:
            raise ConnectionRefusedError(111, "refused")
        return _Conn()


class Run:
    """A `subprocess.run` stand-in. `stdout` is wrapped as the CLI's JSON."""

    def __init__(self, result="ok", stderr="", returncode=0, raw=None, raises=None):
        self.calls = 0
        self.args: list = []
        self.kwargs: dict = {}
        self._raw = raw if raw is not None else json.dumps(
            {"result": result, "usage": {"input_tokens": 1, "output_tokens": 1}}
        )
        self._err, self._rc, self._raises = stderr, returncode, raises

    def __call__(self, *args, **kwargs):
        self.calls += 1
        self.args = list(args[0])
        self.kwargs = kwargs
        if self._raises is not None:
            raise self._raises
        return subprocess.CompletedProcess(
            args=args[0], returncode=self._rc, stdout=self._raw, stderr=self._err
        )


def kit_route(rsp, monkeypatch, tmp_path, url=STUB_URL, accept=True, registry=None):
    """Route `rsp` through the kit with every live input injected. Returns the dialer."""
    dialer = Dialer(accept)
    reg = registry if registry is not None else (lambda: (True, url))
    monkeypatch.setattr(rsp, "KIT_ROOT", tmp_path / "kitroot")
    monkeypatch.setattr(rsp, "_kit_url_source", lambda: kit.base_url(registry=reg, environ={}))
    monkeypatch.setattr(rsp, "_kit_connect", dialer)
    # The parent-side git measurement is stubbed so no arm runs git, and so
    # `subprocess.run` stubs see exactly the one session launch.
    monkeypatch.setattr(rsp, "repo_facts", lambda: "abc1234 a stubbed commit", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _n: str(ROOT / "fake-claude-shim.cmd"))
    return dialer


# ---------------------------------------------------------------------------
# The prefix strip, applied on top of the kit's child env.
# ---------------------------------------------------------------------------


def test_the_variable_names_are_the_directive_names():
    assert he.ENV_HEADLESS_BASE_URL == "CLAUDE_HEADLESS_BASE_URL" == kit.VAR
    assert he.ENV_CHILD_BASE_URL == "ANTHROPIC_BASE_URL"


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


def test_auth_and_routing_vars_never_survive_the_strip():
    """A billing bypass: an inherited key or provider switch outranks the proxy."""
    parent = {name: "inherited-" + name.lower() for name in STRIPPED}
    parent["PATH"] = "p"
    snapshot = dict(parent)
    child = he.harden_child_env(parent)
    leaked = sorted(n for n in STRIPPED if n in child)
    assert leaked == [], f"inherited into the child: {leaked}"
    assert child == {"PATH": "p"}
    assert parent == snapshot, "the strip mutated its input"
    assert child is not parent


def test_r6_every_anthropic_and_claude_code_key_is_dropped_by_prefix():
    parent = {
        "PATH": "p",
        "CLAUDE_CODE_MESSAGING_SOCKET": "s",
        "CLAUDECODE": "1",
        "CLAUDE_CODE_ENTRYPOINT": "cli",
        "ANTHROPIC_MODEL": "m",
        "ANTHROPIC_BASE_URL": STUB_URL,
        "CLAUDE_CODE_GIT_BASH_PATH": "bash.exe",
        "CLAUDE_HEADLESS_BASE_URL": "kept-not-a-prefix",
    }
    child = he.harden_child_env(parent, keep=(he.ENV_CHILD_BASE_URL,))
    assert sorted(child) == sorted(
        ["PATH", "CLAUDE_CODE_GIT_BASH_PATH", "CLAUDE_HEADLESS_BASE_URL", "ANTHROPIC_BASE_URL"]
    ), sorted(child)
    assert child["ANTHROPIC_BASE_URL"] == STUB_URL
    assert parent["CLAUDECODE"] == "1", "the parent mapping was mutated"


def test_keep_is_the_only_exemption_and_without_it_the_url_goes():
    """Non-vacuity for `keep`: the same key is stripped when it is not kept."""
    parent = {"ANTHROPIC_BASE_URL": STUB_URL, "ANTHROPIC_API_KEY": kit.PLACEHOLDER_KEY}
    assert he.harden_child_env(parent) == {}
    assert he.harden_child_env(parent, keep=("ANTHROPIC_BASE_URL",)) == {
        "ANTHROPIC_BASE_URL": STUB_URL
    }


@pytest.mark.skipif(os.name != "nt", reason="Windows environment keys are case-insensitive")
def test_r6_the_prefix_match_is_case_insensitive_on_windows():
    parent = {"anthropic_api_key": "k", "Claude_Code_Oauth_Token": "t", "PATH": "p"}
    assert sorted(he.harden_child_env(parent)) == ["PATH"]


def test_the_strip_list_is_one_named_tuple():
    assert set(STRIPPED) <= set(he.CHILD_ENV_STRIPPED)
    assert isinstance(he.CHILD_ENV_STRIPPED, tuple)
    assert he.ENV_CHILD_BASE_URL not in he.CHILD_ENV_STRIPPED
    uncovered = [n for n in he.CHILD_ENV_STRIPPED if not he._stripped(n)]
    assert uncovered == [], f"named but not covered by the prefix strip: {uncovered}"
    # Non-vacuity: an unrelated key survives the same predicate.
    assert not he._stripped("PATH")


def test_the_deleted_route_stays_deleted():
    """One path, the kit's: this module no longer reads or probes a URL."""
    for gone in ("prepare_headless_env", "resolve_base_url", "probe", "read_user_store"):
        assert not hasattr(he, gone), gone


def test_no_tracked_code_hardcodes_the_proxy_port():
    """The probe target comes from the variable, never from a literal."""
    # Matched as `:<port>`, so a run of digits such as an alphabet constant
    # holding `0123456789` is not a false hit.
    port = str(3000 + 456)
    for path in (Path(he.__file__), RESPONDER_PATH):
        assert ":" + port not in path.read_text(encoding="ascii"), path
    # Non-vacuity: the same check fires on a line that does carry it.
    assert ":" + port in f"http://127.0.0.1:{port}"
    assert ":" + port not in "0123456789", "the neighbour must survive"


# ---------------------------------------------------------------------------
# The responder's one `claude` spawn, through the kit. The module is loaded by
# importlib and its source is never read - a source reader is a shape grader,
# see `tools/gate_mutation_runner.SHAPE_GRADER_MODULES`.
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


@pytest.fixture()
def closed_url():
    """A loopback URL whose port was just released, so a connect is refused."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{port}"


@pytest.fixture()
def trusted(rsp, monkeypatch):
    monkeypatch.setattr(rsp, "workspace_trust", lambda *_a, **_k: (True, "trusted"))


def _no_run_reserved(rsp) -> bool:
    return not rsp.DEFAULT_RUNS.exists() or json.loads(rsp.DEFAULT_RUNS.read_text())["runs"] == []


def test_the_responder_route_is_the_kits_own_by_default(rsp):
    assert rsp._kit_url_source is kit.base_url
    assert rsp._kit_connect is socket.create_connection


def test_a_refused_route_spawns_nothing(rsp, monkeypatch, tmp_path):
    """Unset in a readable store: the kit refuses, nothing starts, no run spent."""
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    dialer = kit_route(rsp, monkeypatch, tmp_path, registry=lambda: (True, None))
    with pytest.raises(rsp.HeadlessRefused) as info:
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert run.calls == 0, "the session was spawned although the route refused"
    assert dialer.dialled == []
    assert kit.VAR in str(info.value)
    assert isinstance(info.value, rsp.SpawnFailed)
    assert _no_run_reserved(rsp), "a refused route spent a run"


def test_a_routed_spawn_carries_the_child_env(rsp, monkeypatch, tmp_path):
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    dialer = kit_route(rsp, monkeypatch, tmp_path)
    assert rsp._spawn_headless("a prompt", rsp.Bounds()) == "ok"
    assert run.calls == 1
    assert run.kwargs["env"].get(he.ENV_CHILD_BASE_URL) == STUB_URL
    assert ("127.0.0.1", 9) in dialer.dialled, "the kit never probed the route"


def test_the_kill_switch_beats_a_stale_process_copy(rsp, monkeypatch, tmp_path):
    """Deleted from the user store, still inherited here: REFUSE, end to end."""
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    kit_route(rsp, monkeypatch, tmp_path)
    monkeypatch.setattr(
        rsp, "_kit_url_source",
        lambda: kit.base_url(registry=lambda: (True, None), environ={kit.VAR: STUB_URL}),
    )
    with pytest.raises(rsp.HeadlessRefused):
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert run.calls == 0


def test_a_non_loopback_url_is_refused_without_a_dial(rsp, monkeypatch, tmp_path):
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    dialer = kit_route(rsp, monkeypatch, tmp_path, url="http://proxy.invalid:9")
    with pytest.raises(rsp.HeadlessRefused):
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert run.calls == 0 and dialer.dialled == []


def test_a_closed_port_is_refused_by_a_real_dial(rsp, monkeypatch, tmp_path, closed_url):
    """The kit's real `socket.create_connection` against a released loopback port."""
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    kit_route(rsp, monkeypatch, tmp_path, url=closed_url)
    monkeypatch.setattr(rsp, "_kit_connect", socket.create_connection)
    with pytest.raises(rsp.HeadlessRefused) as info:
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert run.calls == 0
    # A refusal reason reaches held files and logs; the URL must not.
    assert closed_url not in str(info.value)
    assert closed_url.rsplit(":", 1)[1] not in str(info.value)


def test_a_usage_limit_exit_raises_usage_limited_and_is_not_retried(rsp, monkeypatch, tmp_path):
    run = Run(raw="Claude AI usage limit reached|1900000000", returncode=1)
    monkeypatch.setattr(subprocess, "run", run)
    kit_route(rsp, monkeypatch, tmp_path)
    with pytest.raises(rsp.UsageLimited) as info:
        rsp._spawn_headless("a prompt", rsp.Bounds())
    assert info.value.reset_at == 1900000000.0
    assert run.calls == 1, "a usage limit must not be retried inside the cycle"


def test_a_usage_limit_on_stderr_is_detected(rsp, monkeypatch, tmp_path):
    run = Run(raw="", stderr="API Error: 429 rate_limit_error", returncode=1)
    monkeypatch.setattr(subprocess, "run", run)
    kit_route(rsp, monkeypatch, tmp_path)
    with pytest.raises(rsp.UsageLimited):
        rsp._spawn_headless("a prompt", rsp.Bounds())


def test_a_draft_without_any_limit_phrase_is_a_draft(rsp, monkeypatch, tmp_path):
    """Survival guard. RULED 2026-10-02: a limit phrase ANYWHERE backs off, even
    in a real draft, because a false positive only backs off. So the neighbour
    that must survive is a draft carrying no limit phrase at all."""
    text = rsp.RESPONDER_TAG + "\nThe hop budget held at eight.\n" + "x" * 400
    monkeypatch.setattr(subprocess, "run", Run(text))
    kit_route(rsp, monkeypatch, tmp_path)
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
    rsp, tmp_path, monkeypatch, trusted
):
    run = Run(raw="Claude AI usage limit reached", returncode=1)
    monkeypatch.setattr(subprocess, "run", run)
    dialer = kit_route(rsp, monkeypatch, tmp_path)

    first = _armed_cycle(rsp, tmp_path)
    assert first["termination"] == "usage-limited", first
    until = json.loads(rsp.DEFAULT_BACKOFF.read_text(encoding="ascii"))["until"]
    assert until > time.time()
    dials = len(dialer.dialled)

    second = _armed_cycle(rsp, tmp_path)
    assert second["termination"] == "usage-backoff", second
    assert run.calls == 1, "the backoff did not stop the second spawn"
    assert len(dialer.dialled) == dials, "a backed-off cycle still probed a route"
    for name in ("usage-limited", "usage-backoff", "headless-refused"):
        assert name in rsp.TERMINATIONS, name


def test_the_backoff_expires(rsp, tmp_path, monkeypatch, trusted):
    run = Run(raw="Claude AI usage limit reached", returncode=1)
    monkeypatch.setattr(subprocess, "run", run)
    kit_route(rsp, monkeypatch, tmp_path)
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
    rsp, tmp_path, monkeypatch, trusted
):
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    kit_route(rsp, monkeypatch, tmp_path, accept=False)
    result = _armed_cycle(rsp, tmp_path)
    assert result["termination"] == "headless-refused", result
    assert result["reasons"] == ["proxy unreachable: ConnectionRefusedError"], result
    assert run.calls == 0
    assert not list(rsp.DEFAULT_STAGING.glob("held/*"))


def test_a_plain_spawn_failure_still_reads_spawn_failed(rsp, tmp_path, trusted):
    """Survival guard: the new handlers did not swallow the old one."""

    def broken(prompt, bounds):
        raise rsp.SpawnFailed("FileNotFoundError")

    assert _armed_cycle(rsp, tmp_path, spawn=broken)["termination"] == "spawn-failed"

# ---------------------------------------------------------------------------
# FLEET-KIT v3 rulings around `fleet_headless.spawn` (MAIN 0955 s2 steps 4-5).
# The kit is never edited; its known gaps are closed through its own
# parameters: prompt on STDIN via `run=` (gap 5 moot, untrusted text off argv),
# the permission floor via `extra=` (gap 2), `--bare` with a short brief, the
# kit's note rule by NAME only (gap 3), and the responder's OS-locked budget
# kept beside the kit's. `kit_route` above is imported by the other
# responder arms that drive `_spawn_headless`.
# ---------------------------------------------------------------------------


@pytest.fixture()
def routed(rsp, monkeypatch, tmp_path):
    return kit_route(rsp, monkeypatch, tmp_path)


def test_the_production_bindings_are_the_kits_own(rsp):
    assert rsp._kit_url_source is kit.base_url
    assert rsp.KIT_ROOT == rsp.REPO_ROOT
    assert rsp.SPAWN_BARE is True
    assert rsp.RESPONDER_BRIEF.is_file()


def test_the_prompt_goes_on_stdin_and_never_on_argv(rsp, routed, monkeypatch):
    run = Run("draft")
    monkeypatch.setattr(subprocess, "run", run)
    prompt = "--dangerously-skip-permissions a prompt that must never be an argument"

    assert rsp._spawn_headless(prompt, rsp.Bounds()) == "draft"

    assert run.calls == 1
    # The prompt, then the parent's measured facts (C2), all on stdin.
    assert run.kwargs["input"].startswith(prompt + "\n\n")
    assert not any(prompt in a for a in run.args), run.args
    assert run.args[1] == "-p"


def test_the_kit_argv_layout_is_checked_not_guessed(rsp, monkeypatch):
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    wrapper = rsp._stdin_run([], "the prompt")
    with pytest.raises(rsp.SpawnFailed):
        wrapper(["claude", "--print-something", "x"], env={}, timeout=1)
    assert run.calls == 0
    # C3: `-p` in place is not enough - argv[2] must BE the prompt handed over.
    with pytest.raises(rsp.SpawnFailed):
        wrapper(["claude", "-p", "--model", "sonnet", "the prompt"], env={}, timeout=1)
    assert run.calls == 0
    # Non-vacuity: the kit's real layout passes.
    wrapper(["claude", "-p", "the prompt", "--model", "sonnet"], env={}, timeout=1)
    assert run.calls == 1 and run.kwargs["input"] == "the prompt"


def test_the_argv_is_bare_with_the_brief_and_the_permission_floor(rsp, routed, monkeypatch):
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    rsp._spawn_headless("p", rsp.Bounds())
    argv = run.args

    def value_of(flag):
        assert argv.count(flag) == 1, (flag, argv)
        return argv[argv.index(flag) + 1]

    assert "--bare" in argv
    assert value_of("--append-system-prompt-file") == str(rsp.RESPONDER_BRIEF)
    assert value_of("--permission-mode") == "dontAsk"
    assert value_of("--tools") == "Read,Grep,Glob"
    assert value_of("--allowed-tools") == "Read,Grep,Glob"
    assert not any("bash" in a.lower() for a in argv[argv.index("--model"):]), argv
    assert value_of("--model") == kit.pick_model(False)
    assert "--strict-mcp-config" in argv
    assert value_of("--output-format") == "json"
    assert not any("bypass" in a.lower() or "dangerously" in a.lower() for a in argv), argv


def test_the_brief_is_short_ascii_and_lf(rsp):
    data = rsp.RESPONDER_BRIEF.read_bytes()
    assert data.decode("ascii")
    assert b"\r" not in data
    assert 0 < len(data) < 2048, len(data)


def test_the_child_env_is_the_kits_hardened_by_the_prefix_strip(rsp, routed, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "inherited")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "inherited-key")
    monkeypatch.setenv("CLAUDE_CODE_GIT_BASH_PATH", "bash.exe")
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    rsp._spawn_headless("p", rsp.Bounds())
    env = run.kwargs["env"]

    assert env["ANTHROPIC_BASE_URL"] == STUB_URL
    assert env["ANTHROPIC_API_KEY"] == kit.PLACEHOLDER_KEY, "bare needs the kit's placeholder"
    assert "CLAUDECODE" not in env and "CLAUDE_CODE_OAUTH_TOKEN" not in env
    assert env["CLAUDE_CODE_GIT_BASH_PATH"] == "bash.exe"
    parent_kept = os.environ.get("CLAUDECODE") == "1"
    assert parent_kept, "the parent environment was mutated (key CLAUDECODE)"


def test_the_kit_writes_its_records_under_its_root_and_ends_idle(rsp, routed, monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", Run())
    before = time.time()
    rsp._spawn_headless("p", rsp.Bounds())

    root = tmp_path / "kitroot"
    status = json.loads((root / kit.STATUS_REL).read_text(encoding="ascii"))
    assert status["state"] == "idle" and status["task"] == "Idle"
    assert status["code"] == rsp.SELF_CODE
    assert status["next_tick"] is not None
    assert status["runs_in_window"] == 1
    usage = (root / kit.USAGE_REL).read_text(encoding="ascii").splitlines()
    assert len(usage) == 1 and json.loads(usage[0])["bare"] is True
    starts = json.loads((root / kit.BUDGET_REL).read_text(encoding="ascii"))["starts"]
    assert len(starts) == 1 and starts[0] >= before
    # The responder's own budget reserved its run too.
    assert len(json.loads(rsp.DEFAULT_RUNS.read_text())["runs"]) == 1


def test_a_spent_kit_budget_starts_nothing(rsp, routed, monkeypatch, tmp_path):
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    path = tmp_path / "kitroot" / kit.BUDGET_REL
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"starts": [time.time() - 60.0] * kit.RUNS_CAP}))

    with pytest.raises(rsp.RunBudgetSpent):
        rsp._spawn_headless("p", rsp.Bounds())
    assert run.calls == 0
    assert _no_run_reserved(rsp), "a kit refusal burned a responder run"
    # Non-vacuity: the kit's file is unchanged - the pre-check only read it.
    assert len(json.loads(path.read_text())["starts"]) == kit.RUNS_CAP


def test_a_timeout_is_a_spawn_failure_and_the_lane_still_ends_idle(rsp, routed, monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", Run(raises=subprocess.TimeoutExpired("claude", 1)))
    with pytest.raises(rsp.SpawnFailed) as info:
        rsp._spawn_headless("p", rsp.Bounds())
    assert str(info.value) == "TimeoutExpired"
    status = json.loads((tmp_path / "kitroot" / kit.STATUS_REL).read_text(encoding="ascii"))
    assert status["state"] == "idle", status


def test_a_non_json_print_is_a_failure_not_a_draft(rsp, routed, monkeypatch):
    monkeypatch.setattr(subprocess, "run", Run(raw="plain text, not the CLI's JSON", returncode=1))
    with pytest.raises(rsp.SpawnFailed):
        rsp._spawn_headless("p", rsp.Bounds())


# ---------------------------------------------------------------------------
# The kit's note rule, by name only.
# ---------------------------------------------------------------------------


def _note(inbox: Path, name: str, body: str = "please measure\n") -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / name
    path.write_bytes(body.encode("ascii"))
    return path


def test_a_main_order_discussing_terminal_in_its_body_is_still_queued(rsp, tmp_path):
    """Gap 3: the kit's head test would damp this; head="" keeps it."""
    inbox = tmp_path / "inbox"
    body = "TO RSC.\nNever spawn on a note marked TERMINAL. A reply IS requested.\n"
    kept = _note(inbox, "2026-10-03-1100-from-MAIN-order.md", body)
    assert kit.should_skip(kept.name, "RSC", body) == "terminal", "non-vacuity: the kit would damp it"
    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == [kept]


def test_the_kit_damps_a_terminal_substring_in_a_name(rsp, tmp_path):
    """RECORDED OVER-DAMP: the kit matches TERMINAL as a substring of the name,
    so `terminals` is skipped. Accepted - fleet law, and the safe side."""
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-03-1101-from-RC-terminals-and-replies.md")
    kept = _note(inbox, "2026-10-03-1102-from-RC-question.md")
    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == [kept]


# ---------------------------------------------------------------------------
# Adversary round 1 on a04f4c7: 4a, C2, C5, C6.
# ---------------------------------------------------------------------------

RAW_API_ERROR = "Invalid API key - Please run /login"


def _error_json(rc_result=RAW_API_ERROR):
    return json.dumps({"type": "result", "is_error": True, "result": rc_result})


@pytest.mark.parametrize(
    ("raw", "rc"),
    [
        (_error_json(), 1),
        (_error_json(), 0),
        (json.dumps({"is_error": False, "result": "looks like a draft"}), 1),
    ],
    ids=["is-error-rc1", "is-error-rc0", "clean-json-rc1"],
)
def test_an_error_result_or_a_nonzero_exit_is_never_a_draft(rsp, routed, monkeypatch, caplog, raw, rc):
    monkeypatch.setattr(subprocess, "run", Run(raw=raw, returncode=rc))
    with caplog.at_level("WARNING"):
        with pytest.raises(rsp.SpawnFailed) as info:
            rsp._spawn_headless("p", rsp.Bounds())
    # The raw text is LOGGED for the operator and kept out of the exception,
    # which is what reaches held files, metrics and replies.
    assert RAW_API_ERROR not in str(info.value)
    assert "looks like a draft" not in str(info.value)
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert ("Invalid API key" in logged) or ("looks like a draft" in logged), logged


def test_a_clean_zero_exit_result_is_still_a_draft(rsp, routed, monkeypatch):
    """Survival guard for the arm above."""
    monkeypatch.setattr(
        subprocess, "run", Run(raw=json.dumps({"is_error": False, "result": "a draft"}), returncode=0)
    )
    assert rsp._spawn_headless("p", rsp.Bounds()) == "a draft"


def test_an_is_error_session_reaches_no_held_file_and_no_sibling(rsp, tmp_path, monkeypatch, trusted):
    """The probe: is_error, rc 1, an API string. It must surface nowhere."""
    monkeypatch.setattr(subprocess, "run", Run(raw=_error_json(), returncode=1))
    kit_route(rsp, monkeypatch, tmp_path)
    result = _armed_cycle(rsp, tmp_path)
    assert result["termination"] == "spawn-failed", result
    surfaces = [p for p in (tmp_path / "rc").rglob("*") if p.is_file()]
    surfaces += [p for p in rsp.DEFAULT_STAGING.rglob("*") if p.is_file()]
    surfaces += [p for p in rsp.DEFAULT_METRICS.parent.rglob("*") if p.is_file()]
    leaked = [str(p) for p in surfaces if b"Invalid API key" in p.read_bytes()]
    assert leaked == [], leaked
    assert "Invalid API key" not in json.dumps(result)


def test_the_child_floor_holds_no_bash_entry(rsp):
    """C2: `git log --output=<file>` writes and pytest executes it; no Bash at all."""
    assert not [a for a in rsp.SPAWN_FLOOR if "bash" in a.lower()], rsp.SPAWN_FLOOR
    floor = list(rsp.SPAWN_FLOOR)
    assert floor[floor.index("--tools") + 1] == "Read,Grep,Glob"
    assert floor[floor.index("--allowed-tools") + 1] == "Read,Grep,Glob"
    assert floor[floor.index("--permission-mode") + 1] == "dontAsk"


def test_neither_the_brief_nor_the_prompt_asks_for_a_command(rsp, tmp_path):
    """C2 measured: both used to tell the child to run its suite and git."""
    brief = rsp.RESPONDER_BRIEF.read_text(encoding="ascii")
    note = _note(tmp_path / "inbox", "2026-10-03-1200-from-RC-q.md")
    prompt = rsp.build_prompt(note, rsp.Bounds())
    for text in (brief, prompt):
        low = text.lower()
        assert "python -m pytest" not in low and "run its own suites" not in low
        assert "`git log`" not in low


def test_the_parent_measures_git_log_and_the_child_reads_it(rsp, routed, monkeypatch):
    """The facts the child can no longer measure come from the parent."""
    run = Run()
    monkeypatch.setattr(subprocess, "run", run)
    rsp._spawn_headless("the prompt", rsp.Bounds())
    assert run.kwargs["input"].startswith("the prompt")
    assert "abc1234 a stubbed commit" in run.kwargs["input"]


def test_repo_facts_runs_git_in_the_parent_and_degrades_quietly(rsp, monkeypatch):
    seen = []

    def fake(argv, **kwargs):
        seen.append((list(argv), kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout="abc1234 subject one\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake)
    facts = rsp.repo_facts()
    assert "abc1234 subject one" in facts
    argv, kwargs = seen[0]
    assert argv[0] == "git" and "log" in argv
    assert not any(a.startswith("--output") for a in argv)
    assert kwargs.get("creationflags") == getattr(subprocess, "CREATE_NO_WINDOW", 0)
    assert kwargs.get("timeout")

    def broken(argv, **kwargs):
        raise FileNotFoundError(2, "no git")

    monkeypatch.setattr(subprocess, "run", broken)
    degraded = rsp.repo_facts()
    assert "not measured" in degraded and "no git" not in degraded


def test_node_options_never_reaches_the_child():
    """C5: NODE_OPTIONS can preload code into the node-based CLI."""
    assert he.harden_child_env({"NODE_OPTIONS": "--require x.js", "PATH": "p"}) == {"PATH": "p"}
    # Neighbour survives: another NODE_ key is not swept.
    assert he.harden_child_env({"NODE_ENV": "production"}) == {"NODE_ENV": "production"}


@pytest.mark.parametrize(
    "name",
    [
        "2026-10-03-1300-from-MAIN-ORDER-fix-the-terminal-rule.md",
        "2026-10-03-1301-from-MAIN-ORDER-TERMINALS-sweep.md",
        "2026-10-03-1302-from-MAIN-ORDER-no-reply-loops-RSC.md",
    ],
)
def test_a_main_order_is_not_damped_by_the_kits_name_test(rsp, tmp_path, name):
    """C6: for MAIN the kit's substring name test is not applied; this tree's
    narrow check decides. Each of these is an ORDER, not a declaration."""
    inbox = tmp_path / "inbox"
    kept = _note(inbox, name, "TO RSC. Do the thing; a reply is requested.\n")
    assert kit.should_skip(name, "RSC", "") == "terminal", "non-vacuity: the kit would damp it"
    if "no-reply" in name:
        # This tree's own check treats a hyphenated no-reply token as a
        # declaration, so this one stays skipped - recorded, not hidden.
        assert rsp.pending(inbox, rsp.OPTED_IN, set()) == []
    else:
        assert rsp.pending(inbox, rsp.OPTED_IN, set()) == [kept]


def test_a_main_note_that_declares_terminal_is_still_skipped(rsp, tmp_path):
    """The neighbour: a MAIN declaration is still damped by this tree's check."""
    inbox = tmp_path / "inbox"
    _note(inbox, "2026-10-03-1303-from-MAIN-ACK-x-TERMINAL.md")
    _note(inbox, "2026-10-03-1304-from-MAIN-ack.md", "TO RSC. TERMINAL, no reply wanted.\n")
    assert rsp.pending(inbox, rsp.OPTED_IN, set()) == []
