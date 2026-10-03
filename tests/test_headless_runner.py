"""Tests for the headless runner entrypoint.

The exit-code assertions go through `subprocess` deliberately. Calling
`runner.main([...])` in-process tests a function; CI runs a COMMAND, and the
difference between the two is where the interesting failures live - a module
that is not importable as `-m`, an argparse error path that raises instead of
returning, a stray import that needs the network. `python -m headless.runner
--once --dry-run` is the literal CI smoke test, so it is exercised literally.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from headless import jobs as jobs_mod
from headless import runner as runner_mod
from ops import health as health_mod
from ops.loop import slots as slots_mod

REPO_ROOT = Path(__file__).resolve().parents[1]

SMOKE_TEST = ["--once", "--dry-run"]


def _slot_redirect_prelude(slot_root: Path) -> str:
    """Python source that points the child's slot bucket at `slot_root`.

    `slots.hold` reads the module-level `DEFAULT_ROOT` at CALL time, so
    rebinding it before the runner runs redirects every acquisition. Without
    this a live child acquires in the MACHINE-WIDE bucket under C:\\ProgramData.
    """
    return (
        "import pathlib as _pathlib\n"
        "from ops.loop import slots as _slots\n"
        f"_slots.DEFAULT_ROOT = _pathlib.Path({str(slot_root)!r})\n"
    )


def run_cli(
    args: list[str],
    cwd: Path,
    runtime_dir: Path | None = None,
    slot_root: Path | None = None,
) -> subprocess.CompletedProcess:
    """Invoke the real entrypoint the way CI does.

    `cwd` is a temp directory, not the repo, so any stray file the runner
    writes lands somewhere the test can see it. The repo reaches the child
    through PYTHONPATH instead.

    `slot_root` is REQUIRED for a live invocation - see the guard at the foot
    of this module. With it the child runs `headless.runner` as `__main__`
    through `runpy`, the same module-as-script path `-m` takes, after the slot
    bucket has been redirected. A dry run keeps the literal `-m` command.
    """
    # One binding with `sys.executable` as its literal head, so the
    # interpreter-pinning census can resolve argv[0]. Only the tail varies.
    tail = (
        [
            "-c",
            _slot_redirect_prelude(slot_root)
            + "import runpy, sys\n"
            + f"sys.argv = ['headless.runner', *{list(args)!r}]\n"
            + "runpy.run_module('headless.runner', run_name='__main__', alter_sys=True)\n",
        ]
        if slot_root is not None
        else ["-m", "headless.runner", *args]
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env.pop("RESINCOMPUTE_UID", None)
    # No test in this suite is allowed to reach the network. The dry-run cases
    # would not anyway; the live-pass cases would, so the kill switch is set
    # for all of them rather than only the ones that currently need it.
    env[jobs_mod.ENV_OFFLINE] = "1"
    if runtime_dir is not None:
        env[health_mod.ENV_RUNTIME_DIR] = str(runtime_dir)
    else:
        env.pop(health_mod.ENV_RUNTIME_DIR, None)
    return subprocess.run(
        [sys.executable, *tail],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture()
def clean_registry():
    snapshot = jobs_mod.registry_snapshot()
    yield
    jobs_mod.restore_registry(snapshot)


# ---------------------------------------------------------------------------
# --list-jobs
# ---------------------------------------------------------------------------


def test_list_jobs_exits_zero_and_lists_every_registered_job(tmp_path: Path) -> None:
    proc = run_cli(["--list-jobs"], cwd=tmp_path, runtime_dir=tmp_path / "runtime")
    assert proc.returncode == 0, proc.stderr
    for name in jobs_mod.job_names():
        assert name in proc.stdout, f"{name} missing from --list-jobs output"
    assert f"{len(jobs_mod.job_names())} registered job(s)" in proc.stdout


def test_list_jobs_writes_nothing(tmp_path: Path) -> None:
    """Listing is a read. It must not create the runtime directory."""
    runtime = tmp_path / "runtime"
    proc = run_cli(["--list-jobs"], cwd=tmp_path, runtime_dir=runtime)
    assert proc.returncode == 0
    assert not runtime.exists()
    assert list(tmp_path.iterdir()) == []


def test_list_jobs_runs_no_job(tmp_path: Path) -> None:
    proc = run_cli(["--list-jobs"], cwd=tmp_path, runtime_dir=tmp_path / "runtime")
    assert "pass start" not in proc.stderr
    assert "pass complete" not in proc.stderr


# ---------------------------------------------------------------------------
# The CI smoke test
# ---------------------------------------------------------------------------


def test_the_ci_smoke_test_exits_zero(tmp_path: Path) -> None:
    """`python -m headless.runner --once --dry-run`. CI depends on this exit code."""
    proc = run_cli(SMOKE_TEST, cwd=tmp_path, runtime_dir=tmp_path / "runtime")
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert "pass complete" in proc.stderr


def test_the_smoke_test_writes_nothing(tmp_path: Path) -> None:
    """A dry run computes and logs. It does not write - not even a log file."""
    runtime = tmp_path / "runtime"
    proc = run_cli(SMOKE_TEST, cwd=tmp_path, runtime_dir=runtime)
    assert proc.returncode == 0, proc.stderr
    assert not runtime.exists(), "a dry run created the runtime directory"
    leftovers = sorted(p.name for p in tmp_path.rglob("*"))
    assert leftovers == [], f"a dry run wrote {leftovers}"


def test_the_smoke_test_runs_every_job(tmp_path: Path) -> None:
    proc = run_cli(SMOKE_TEST, cwd=tmp_path, runtime_dir=tmp_path / "runtime")
    for name in jobs_mod.job_names():
        assert name in proc.stderr, f"{name} did not report in the pass"


def test_the_smoke_test_reports_a_status_for_every_job(tmp_path: Path) -> None:
    """Every job logs exactly one PASS / FAIL / SKIP line."""
    proc = run_cli(SMOKE_TEST, cwd=tmp_path, runtime_dir=tmp_path / "runtime")
    known = {"PASS", "FAIL", "SKIP"}
    statuses = []
    for line in proc.stderr.splitlines():
        found = [token for token in line.split() if token in known]
        if found:
            statuses.append(found[0])
    assert len(statuses) == len(jobs_mod.job_names()), proc.stderr
    assert "FAIL" not in statuses


def test_a_bare_invocation_runs_one_pass(tmp_path: Path) -> None:
    """No mode flag defaults to a single pass rather than doing nothing."""
    runtime = tmp_path / "runtime"
    proc = run_cli(["--dry-run"], cwd=tmp_path, runtime_dir=runtime)
    assert proc.returncode == 0, proc.stderr
    assert "pass complete" in proc.stderr


# ---------------------------------------------------------------------------
# --job
# ---------------------------------------------------------------------------


def test_job_flag_runs_only_that_job(tmp_path: Path) -> None:
    proc = run_cli(
        ["--once", "--dry-run", "--job", "emit_health"],
        cwd=tmp_path,
        runtime_dir=tmp_path / "runtime",
    )
    assert proc.returncode == 0, proc.stderr
    assert "1 job(s)" in proc.stderr
    assert "emit_health" in proc.stderr
    # Its declared dependencies are NOT pulled in: --job means "instead of".
    for other in ("sync_profile", "reconcile_state", "recompute_plan", "forecast_pity"):
        assert other not in proc.stderr, f"--job emit_health also ran {other}"


def test_job_flag_is_repeatable(tmp_path: Path) -> None:
    proc = run_cli(
        ["--once", "--dry-run", "--job", "sync_profile", "--job", "emit_health"],
        cwd=tmp_path,
        runtime_dir=tmp_path / "runtime",
    )
    assert proc.returncode == 0, proc.stderr
    assert "2 job(s)" in proc.stderr
    assert "sync_profile" in proc.stderr
    assert "emit_health" in proc.stderr
    assert "recompute_plan" not in proc.stderr


def test_an_unknown_job_name_exits_non_zero_with_a_friendly_message(tmp_path: Path) -> None:
    proc = run_cli(
        ["--once", "--dry-run", "--job", "not_a_real_job"],
        cwd=tmp_path,
        runtime_dir=tmp_path / "runtime",
    )
    assert proc.returncode != 0
    assert proc.returncode == runner_mod.EXIT_USAGE
    assert "not_a_real_job" in proc.stderr
    assert "--list-jobs" in proc.stderr
    # A friendly message, not a traceback.
    assert "Traceback" not in proc.stderr
    assert "KeyError" not in proc.stderr


def test_an_unknown_job_name_names_the_valid_options(tmp_path: Path) -> None:
    proc = run_cli(
        ["--once", "--job", "nope"],
        cwd=tmp_path,
        runtime_dir=tmp_path / "runtime",
        slot_root=tmp_path / "slots",
    )
    for name in jobs_mod.job_names():
        assert name in proc.stderr


def test_an_unknown_job_name_runs_nothing(tmp_path: Path) -> None:
    """Validation happens before any work starts."""
    runtime = tmp_path / "runtime"
    slot_root = tmp_path / "slots"
    proc = run_cli(
        ["--once", "--job", "nope"], cwd=tmp_path, runtime_dir=runtime, slot_root=slot_root
    )
    assert proc.returncode == runner_mod.EXIT_USAGE
    assert "pass start" not in proc.stderr
    assert not runtime.exists()
    assert not slot_root.exists(), "a usage error reached the slot bucket"


def test_select_jobs_preserves_registry_order_not_argument_order() -> None:
    """Asking for them backwards still runs them in dependency order."""
    selected = runner_mod.select_jobs(["emit_health", "sync_profile"])
    assert [spec.name for spec in selected] == ["sync_profile", "emit_health"]


def test_select_jobs_with_no_names_returns_the_whole_registry() -> None:
    assert [s.name for s in runner_mod.select_jobs(None)] == jobs_mod.job_names()
    assert [s.name for s in runner_mod.select_jobs([])] == jobs_mod.job_names()


def test_select_jobs_raises_key_error_on_an_unknown_name() -> None:
    with pytest.raises(KeyError):
        runner_mod.select_jobs(["nope"])


# ---------------------------------------------------------------------------
# A failing job does not abort the pass
# ---------------------------------------------------------------------------


def test_a_raising_job_does_not_abort_the_pass(clean_registry, tmp_path: Path) -> None:
    """The jobs after it still run, and it is reported FAIL."""

    def _explode(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        raise RuntimeError("internal detail 0xdeadbeef")

    jobs_mod.register(
        jobs_mod.JobSpec(
            name="explode",
            description="always raises",
            cadence=jobs_mod.CADENCE_ON_DEMAND,
            func=_explode,
        )
    )

    outcome = runner_mod.run_pass(dry_run=True, runtime_dir=str(tmp_path))

    names = [r.name for r in outcome.results]
    assert names == jobs_mod.job_names(), "the pass stopped early"
    assert "explode" in names

    exploded = next(r for r in outcome.results if r.name == "explode")
    assert exploded.status == jobs_mod.STATUS_FAIL
    assert "0xdeadbeef" not in exploded.message
    # Everything else still reported.
    assert len(outcome.results) == len(jobs_mod.job_names())
    assert outcome.counts()[jobs_mod.STATUS_FAIL] == 1
    assert not outcome.ok


def test_a_failing_job_exits_non_zero_in_a_live_run(tmp_path: Path) -> None:
    """Through the real CLI, so the exit code is the one CI would observe.

    A driver script registers a raising job and then calls `main`, which is the
    only way to inject a failure into a genuine subprocess invocation.
    """
    runtime = tmp_path / "runtime"
    slot_root = tmp_path / "slots"
    driver = tmp_path / "driver.py"
    driver.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
        + _slot_redirect_prelude(slot_root)
        + "from headless import jobs, runner\n"
        "@jobs.job(name='always_fails', description='x', cadence=jobs.CADENCE_ON_DEMAND)\n"
        "def _boom(context):\n"
        "    raise RuntimeError('raw upstream detail 0xdeadbeef')\n"
        "sys.exit(runner.main(['--once', '--job', 'always_fails']))\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env[jobs_mod.ENV_OFFLINE] = "1"
    env[health_mod.ENV_RUNTIME_DIR] = str(runtime)
    proc = subprocess.run(
        [sys.executable, str(driver)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == runner_mod.EXIT_JOB_FAILED, proc.stderr
    assert slot_root.is_dir(), "the live pass never reached the redirected bucket"
    assert list(slot_root.glob("*.lock")) == [], "the live pass leaked its slot"

    payload = json.loads((runtime / health_mod.HEALTH_FILENAME).read_text(encoding="utf-8"))
    assert payload["last_pass_ok"] is False
    entry = next(j for j in payload["jobs"] if j["name"] == "always_fails")
    assert entry["status"] == "FAIL"
    # The raw exception text is logged, never written into the health file.
    assert "0xdeadbeef" not in entry["message"]


def test_a_dry_run_never_fails_the_exit_code_on_a_job_outcome(
    clean_registry, tmp_path: Path
) -> None:
    """A dry run promised only to compute and log, and it did."""

    def _explode(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        raise RuntimeError("boom")

    jobs_mod.register(
        jobs_mod.JobSpec(
            name="explode", description="x", cadence=jobs_mod.CADENCE_ON_DEMAND, func=_explode
        )
    )
    assert runner_mod.main(["--once", "--dry-run"]) == runner_mod.EXIT_OK


# ---------------------------------------------------------------------------
# The live pass writes the summary
# ---------------------------------------------------------------------------


def test_a_live_pass_writes_the_run_summary(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    slot_root = tmp_path / "slots"
    proc = run_cli(
        ["--once", "--uid", "900000000"],
        cwd=tmp_path,
        runtime_dir=runtime,
        slot_root=slot_root,
    )
    assert proc.returncode == 0, proc.stderr
    # Positive control on the redirect: the live pass acquired in the private
    # bucket (so it exists) and released (so it holds no lock).
    assert slot_root.is_dir(), "the live pass never reached the redirected bucket"
    assert list(slot_root.glob("*.lock")) == [], "the live pass leaked its slot"

    payload = json.loads((runtime / health_mod.HEALTH_FILENAME).read_text(encoding="utf-8"))
    assert payload["version"] == health_mod.SCHEMA_VERSION
    assert payload["alive"] is True
    assert payload["uid"] == "900000000"
    assert payload["role"] == "headless-runner"
    assert payload["last_pass_ok"] is True
    assert [j["name"] for j in payload["jobs"]] == jobs_mod.job_names()
    assert health_mod.is_stale(payload, 300) is False


def test_the_uid_falls_back_to_the_environment(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["RESINCOMPUTE_UID"] = "800000000"
    env[jobs_mod.ENV_OFFLINE] = "1"
    env[health_mod.ENV_RUNTIME_DIR] = str(tmp_path / "runtime")
    proc = subprocess.run(
        [sys.executable, "-m", "headless.runner", "--once", "--dry-run"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "uid=800000000" in proc.stderr


# ---------------------------------------------------------------------------
# Daemon
# ---------------------------------------------------------------------------


def test_the_daemon_stops_at_max_passes(tmp_path: Path) -> None:
    """Bounded so a supervised run can be exercised without a signal."""
    proc = run_cli(
        ["--daemon", "--dry-run", "--interval", "1", "--max-passes", "2"],
        cwd=tmp_path,
        runtime_dir=tmp_path / "runtime",
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr.count("pass complete") == 2
    assert "daemon stopped after 2 pass(es)" in proc.stderr


def test_signal_handler_installation_never_raises() -> None:
    """A platform without SIGTERM degrades; it does not crash the daemon."""
    flag = runner_mod._ShutdownFlag()
    installed = runner_mod.install_signal_handlers(flag)
    assert isinstance(installed, list)
    assert not flag.requested


def test_the_shutdown_flag_wakes_the_wait_early() -> None:
    flag = runner_mod._ShutdownFlag()
    flag.request("test")
    assert flag.requested
    assert flag.wait(30) is True


# ---------------------------------------------------------------------------
# Argument surface
# ---------------------------------------------------------------------------


def test_the_documented_cli_surface_exists() -> None:
    """Every flag the brief names is present with the documented default."""
    parser = runner_mod.build_parser()
    args = parser.parse_args([])
    assert args.once is False
    assert args.daemon is False
    assert args.interval == runner_mod.DEFAULT_INTERVAL_SECONDS == 300
    assert args.dry_run is False
    assert args.job_names is None
    assert args.list_jobs is False
    assert args.uid is None
    assert args.log_level == "INFO"


def test_once_and_daemon_are_mutually_exclusive(tmp_path: Path) -> None:
    proc = run_cli(
        ["--once", "--daemon"],
        cwd=tmp_path,
        runtime_dir=tmp_path / "runtime",
        slot_root=tmp_path / "slots",
    )
    assert proc.returncode == runner_mod.EXIT_USAGE


def test_an_invalid_log_level_falls_back_rather_than_crashing(tmp_path: Path) -> None:
    proc = run_cli(
        ["--once", "--dry-run", "--log-level", "LOUD"],
        cwd=tmp_path,
        runtime_dir=tmp_path / "runtime",
    )
    assert proc.returncode == 0, proc.stderr


# ---------------------------------------------------------------------------
# EARLY WARNING, NOT THE FENCE: live child invocations redirect the slot bucket
# ---------------------------------------------------------------------------
#
# A LIVE pass - `--once` or `--daemon` without `--dry-run` - holds a lane slot in
# `ops.loop.slots.DEFAULT_ROOT`, a MACHINE-WIDE bucket under C:\ProgramData that
# sibling repositories hold against for real. A child process cannot receive a
# `slot_root` keyword, so every live child here must be launched with the bucket
# redirected to a temp directory: `run_cli(..., slot_root=...)` for a CLI arm,
# `_slot_redirect_prelude(...)` inside a driver script for a `runner.main` arm.
#
# THIS IS A SHAPE MATCHER AND IT CANNOT CARRY THE CLAIM "NO ARM REACHES THE
# BUCKET". An adversary measured it missing 11 of 13 synthetic shapes, and an
# in-process `runner_mod.main(["--once"])` is invisible to it by construction.
# The FENCE is the audit hook in the root `conftest.py`. EXACTLY WHAT IT FENCES:
# an audit event in its `_FENCED_EVENTS` table, raised in the PYTEST
# interpreter, whose path argument normalises (normpath, normcase, cwd-joined
# when relative) to the real `DEFAULT_ROOT` or a path under it. WHAT IT DOES NOT
# FENCE: alias spellings of the bucket (`\\?\C:\...`, `\\.\C:\...`, the 8.3
# short name `PROGRA~3`, a trailing dot or space, `\\localhost\C$\...`,
# junctions, symlinks, `subst` drives); native IO with no path event, such as
# `sqlite3` and `ctypes` `CreateFileW`; events outside its table; reads with no
# event such as `os.stat`; `dir_fd`-relative calls; and EVERY CHILD PROCESS,
# because audit hooks do not cross a process boundary. This early warning parses
# ONLY THIS FILE, so it watches the literal child launches written here and
# nothing else: a child process launched from any other test file is watched by
# no guard in the pytest process - except that a child pytest loading a copy of
# the root conftest installs its own fence inside that child. It catches the common literal shapes cheaply; treat a green
# here as "no known shape in this file", never as "no child reaches the bucket".

#: Flags that make an invocation write-free and slot-free. Anything else is live.
_SLOT_FREE_FLAGS = frozenset({"--dry-run", "--list-jobs"})

#: A driver-script call WITH a literal argv. Module level on purpose: the scan
#: reads string constants inside FUNCTION bodies, so a marker spelled inside
#: the scanner would be read as a live driver by the scanner itself.
_DRIVER_MARKER = "runner.main(["


def _str_elts(node: ast.List) -> list[str]:
    return [
        e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)
    ]


def _resolve_args(node: ast.expr, names: dict[str, list[str]]) -> list[str] | None:
    """A literal argv, or None when it cannot be read statically."""
    if isinstance(node, ast.List) and all(
        isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts
    ):
        return _str_elts(node)
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    return None


def _early_warning_live_child_sites(source: str) -> tuple[int, list[str]]:
    """Return (live child sites found, the ones that do NOT redirect the bucket).

    Three shapes are read: a `run_cli(...)` call, a driver script whose text
    calls `runner.main(`, and a bare argv list naming `headless.runner`. An argv
    that cannot be read statically is reported UNRESOLVED, never as clean.
    """
    tree = ast.parse(source)
    names: dict[str, list[str]] = {}
    for stmt in tree.body:
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.List)
        ):
            names[stmt.targets[0].id] = _str_elts(stmt.value)

    live = 0
    bad: list[str] = []
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        if func.name == "run_cli":
            # The helper itself. Its every CALLER is checked by the first rule.
            continue
        calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
        for call in calls:
            if isinstance(call.func, ast.Name) and call.func.id == "run_cli" and call.args:
                argv = _resolve_args(call.args[0], names)
                if argv is None:
                    bad.append(f"line {call.lineno}: UNRESOLVED run_cli argv")
                    continue
                if _SLOT_FREE_FLAGS & set(argv):
                    continue
                live += 1
                if "slot_root" not in {kw.arg for kw in call.keywords}:
                    bad.append(f"line {call.lineno}: live run_cli {argv} without slot_root")
        fragments = [
            n.value for n in ast.walk(func)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        ]
        drivers = [f for f in fragments if _DRIVER_MARKER in f]
        if drivers and not any(_SLOT_FREE_FLAGS & set(f.split("'")) for f in drivers):
            live += 1
            redirected = any(
                isinstance(c.func, ast.Name) and c.func.id == "_slot_redirect_prelude"
                for c in calls
            )
            if not redirected:
                bad.append(f"line {func.lineno}: live runner.main driver in {func.name}")
        for lst in (n for n in ast.walk(func) if isinstance(n, ast.List)):
            argv = _str_elts(lst)
            if "headless.runner" in argv and not (_SLOT_FREE_FLAGS & set(argv)):
                live += 1
                bad.append(f"line {lst.lineno}: live bare headless.runner argv {argv}")
    return live, bad


def test_early_warning_live_child_invocations_redirect_the_slot_bucket() -> None:
    live, bad = _early_warning_live_child_sites(Path(__file__).read_text(encoding="utf-8"))
    assert live >= 2, (
        f"the guard found only {live} live child site(s) in this module, so it is "
        "no longer looking at the arms it exists to police"
    )
    assert bad == [], (
        "a live child invocation here would acquire in the MACHINE-WIDE bucket "
        f"{slots_mod.DEFAULT_ROOT}, which sibling repositories hold live: {bad}"
    )


def test_the_slot_guard_fires_on_every_unredirected_shape_and_spares_dry_ones() -> None:
    """Non-vacuity, and the neighbours: each bad shape is caught, dry ones are not."""
    source = (
        "SMOKE = ['--once', '--dry-run']\n"
        "def test_cli(tmp_path):\n"
        "    run_cli(['--once', '--uid', '1'], cwd=tmp_path)\n"
        "def test_driver(tmp_path):\n"
        "    text = \"sys.exit(runner.main(['--once', '--job', 'x']))\"\n"
        "def test_bare(tmp_path):\n"
        "    subprocess.run([sys.executable, '-m', 'headless.runner', '--once'])\n"
        "def test_opaque(tmp_path, argv):\n"
        "    run_cli(argv, cwd=tmp_path)\n"
        "def test_dry_cli(tmp_path):\n"
        "    run_cli(SMOKE, cwd=tmp_path)\n"
        "def test_dry_bare(tmp_path):\n"
        "    subprocess.run([sys.executable, '-m', 'headless.runner', '--once', '--dry-run'])\n"
        "def test_dry_driver(tmp_path):\n"
        "    text = \"runner.main(['--once', '--dry-run'])\"\n"
        "def test_good_cli(tmp_path):\n"
        "    run_cli(['--once'], cwd=tmp_path, slot_root=tmp_path)\n"
        "def test_good_driver(tmp_path):\n"
        "    text = _slot_redirect_prelude(tmp_path) + \"runner.main(['--once'])\"\n"
    )
    live, bad = _early_warning_live_child_sites(source)
    joined = "\n".join(bad)
    assert len(bad) == 4, bad
    assert "line 3: live run_cli" in joined
    assert "live runner.main driver in test_driver" in joined
    assert "live bare headless.runner" in joined
    assert "UNRESOLVED" in joined
    assert live == 5, f"the two redirected live arms were not counted as live: {live}"
