"""Tests for the headless job registry.

Two properties are the whole point of this file:

1. **Every job degrades to SKIP rather than raising when its dependency is
   unavailable.** Sibling slices are absent during a parallel build and in a
   partial deployment, so "absent" has to be an ordinary reported state. A job
   that raises on a missing import takes the pass down with it.
2. **The registry order is deterministic.** Several orders satisfy the
   dependency graph; exactly one is emitted, on every run and every platform.
   A non-deterministic pass makes a health file impossible to diff.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from headless import jobs as jobs_mod

# The jobs the registry ships with, in the order they must always execute.
# sync_profile before reconcile_state before the two consumers, health last.
EXPECTED_ORDER = [
    "sync_profile",
    "reconcile_state",
    "recompute_plan",
    "forecast_pity",
    "emit_health",
]

# Jobs that cannot do anything useful without a sibling slice. Each must SKIP,
# never FAIL and never raise, when that slice is missing.
DEPENDENCY_BOUND = ["sync_profile", "reconcile_state", "recompute_plan", "forecast_pity"]


@pytest.fixture()
def clean_registry():
    """Restore the registry after a test that adds or removes jobs."""
    snapshot = jobs_mod.registry_snapshot()
    yield
    jobs_mod.restore_registry(snapshot)


@pytest.fixture(autouse=True)
def never_touch_the_network(monkeypatch):
    """Hard-block upstream fetches for every test in this module.

    Belt and braces. Most tests here stub `_try_import` and would not reach a
    transport anyway, but a test that forgets to is a test that hits
    enka.network from CI, and the upstream policy explicitly forbids bulk
    traffic. The kill switch is asserted, not assumed, so a test that WANTS the
    fetch path has to clear it deliberately.
    """
    monkeypatch.setenv(jobs_mod.ENV_OFFLINE, "1")


# ---------------------------------------------------------------------------
# Registry shape and ordering
# ---------------------------------------------------------------------------


def test_every_expected_job_is_registered() -> None:
    assert jobs_mod.job_names() == EXPECTED_ORDER


def test_registry_order_is_deterministic() -> None:
    """Same registry contents, same order. Every time."""
    first = [spec.name for spec in jobs_mod.ordered_jobs()]
    for _ in range(10):
        assert [spec.name for spec in jobs_mod.ordered_jobs()] == first


def test_order_respects_every_declared_dependency() -> None:
    order = jobs_mod.job_names()
    position = {name: index for index, name in enumerate(order)}
    for spec in jobs_mod.ordered_jobs():
        for dependency in spec.depends_on:
            assert dependency in position, f"{spec.name} depends on unregistered {dependency}"
            assert position[dependency] < position[spec.name], (
                f"{spec.name} runs before its dependency {dependency}"
            )


def test_emit_health_runs_last() -> None:
    """The heartbeat must reflect the pass that produced it."""
    assert jobs_mod.job_names()[-1] == "emit_health"


def test_every_spec_carries_a_description_and_a_cadence() -> None:
    valid = {
        jobs_mod.CADENCE_PER_PASS,
        jobs_mod.CADENCE_DAILY,
        jobs_mod.CADENCE_WEEKLY,
        jobs_mod.CADENCE_ON_DEMAND,
    }
    for spec in jobs_mod.ordered_jobs():
        assert spec.description, f"{spec.name} has no description"
        assert spec.cadence in valid, f"{spec.name} has cadence {spec.cadence}"


def test_the_decorator_registers_and_returns_the_function(clean_registry) -> None:
    @jobs_mod.job(name="probe_job", description="a probe", cadence=jobs_mod.CADENCE_ON_DEMAND)
    def _probe(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        return jobs_mod.passed("probe_job", "ran")

    spec = jobs_mod.get_job("probe_job")
    assert spec is not None
    assert spec.description == "a probe"
    assert spec.cadence == jobs_mod.CADENCE_ON_DEMAND
    # The function is returned unchanged, so it stays directly callable.
    assert _probe(jobs_mod.JobContext()).ok


def test_a_duplicate_job_name_is_rejected(clean_registry) -> None:
    """Two jobs under one name would make --job ambiguous."""
    with pytest.raises(ValueError, match="duplicate job name"):

        @jobs_mod.job(name="sync_profile", description="shadow")
        def _shadow(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
            return jobs_mod.passed("sync_profile")


def test_a_dependency_on_an_unregistered_job_is_ignored(clean_registry) -> None:
    """A deployment may not install every job. That must not stop the pass."""
    jobs_mod.restore_registry({})

    @jobs_mod.job(name="lonely", description="x", depends_on=("never_installed",))
    def _lonely(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        return jobs_mod.passed("lonely")

    assert jobs_mod.job_names() == ["lonely"]


def test_a_dependency_cycle_does_not_hang(clean_registry) -> None:
    """A cycle degrades to declaration order rather than deadlocking."""
    jobs_mod.restore_registry({})

    @jobs_mod.job(name="alpha", description="x", depends_on=("beta",))
    def _alpha(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        return jobs_mod.passed("alpha")

    @jobs_mod.job(name="beta", description="x", depends_on=("alpha",))
    def _beta(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        return jobs_mod.passed("beta")

    assert sorted(jobs_mod.job_names()) == ["alpha", "beta"]


def test_unregister_is_idempotent(clean_registry) -> None:
    jobs_mod.unregister("sync_profile")
    jobs_mod.unregister("sync_profile")
    assert "sync_profile" not in jobs_mod.job_names()


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


def test_every_job_skips_on_an_empty_context() -> None:
    """No uid, no state, nothing configured. Every job reports SKIP.

    This is the CI smoke test's shape. Nothing here may FAIL and nothing may
    raise, whether or not the sibling slices happen to be present in the tree
    the test runs against.
    """
    context = jobs_mod.JobContext(dry_run=True)
    for spec in jobs_mod.ordered_jobs():
        result = jobs_mod.run_job(spec, context)
        context.results[spec.name] = result
        assert isinstance(result, jobs_mod.JobResult)
        assert result.status == jobs_mod.STATUS_SKIP, f"{spec.name}: {result.message}"
        assert result.message, f"{spec.name} skipped without saying why"


def test_dependency_bound_jobs_skip_when_the_slice_is_missing(
    monkeypatch, tmp_path: Path
) -> None:
    """Force every optional import to fail and assert SKIP, not FAIL.

    Monkeypatching `_try_import` is what makes this deterministic. Relying on
    the slices genuinely being absent would make the test pass today and
    silently stop testing anything the moment they land.
    """
    monkeypatch.setattr(jobs_mod, "_try_import", lambda dotted: None)
    context = jobs_mod.JobContext(
        uid="900000000", dry_run=False, runtime_dir=str(tmp_path)
    )
    for spec in jobs_mod.ordered_jobs():
        result = jobs_mod.run_job(spec, context)
        context.results[spec.name] = result
        assert not result.failed, f"{spec.name} failed instead of skipping: {result.message}"
        if spec.name in DEPENDENCY_BOUND:
            assert result.status == jobs_mod.STATUS_SKIP, f"{spec.name}: {result.message}"


def test_sync_profile_skips_without_a_uid() -> None:
    result = jobs_mod.sync_profile(jobs_mod.JobContext())
    assert result.skipped
    assert "uid" in result.message


def test_sync_profile_skips_when_the_ingest_slice_is_absent(monkeypatch) -> None:
    monkeypatch.setattr(jobs_mod, "_try_import", lambda dotted: None)
    result = jobs_mod.sync_profile(jobs_mod.JobContext(uid="900000000"))
    assert result.skipped
    assert "ingest" in result.message


def test_sync_profile_skips_in_offline_mode(monkeypatch) -> None:
    """The kill switch stops the fetch before any transport is constructed."""

    class _WouldFetch:
        @staticmethod
        def fetch_profile(uid: str):
            raise AssertionError("offline mode still reached the transport")

    monkeypatch.setattr(jobs_mod, "_try_import", lambda dotted: _WouldFetch)
    monkeypatch.setenv(jobs_mod.ENV_OFFLINE, "1")
    result = jobs_mod.sync_profile(jobs_mod.JobContext(uid="900000000"))
    assert result.skipped
    assert jobs_mod.ENV_OFFLINE in result.message


def test_the_offline_switch_reads_the_usual_truthy_spellings(monkeypatch) -> None:
    for value in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv(jobs_mod.ENV_OFFLINE, value)
        assert jobs_mod.is_offline() is True, value
    for value in ("0", "false", "no", "", "off"):
        monkeypatch.setenv(jobs_mod.ENV_OFFLINE, value)
        assert jobs_mod.is_offline() is False, value


def test_sync_profile_reports_fail_when_a_present_client_misbehaves(monkeypatch) -> None:
    """Absent is a SKIP. Present-and-broken is a FAIL. The two are different."""

    class _Broken:
        @staticmethod
        def fetch_profile(uid: str):
            raise RuntimeError("upstream returned 503 for uid " + uid)

    monkeypatch.setattr(jobs_mod, "_try_import", lambda dotted: _Broken)
    monkeypatch.setenv(jobs_mod.ENV_OFFLINE, "0")
    result = jobs_mod.sync_profile(jobs_mod.JobContext(uid="900000000"))
    assert result.failed
    # The raw upstream string never reaches the reported message.
    assert "503" not in result.message
    assert "see the log" in result.message


def test_sync_profile_passes_through_the_clients_friendly_message(monkeypatch) -> None:
    """A refusal is reported in the client's own operator-safe words.

    `FetchResult.friendly_message` is built by the ingest slice for exactly
    this purpose, so passing it through is not a raw-error leak. The test pins
    that it is the friendly field that travels, not a status code or an
    exception repr.
    """

    class _Refused:
        ok = False
        friendly_message = "profile is private - open the character showcase in game"
        profile_json = None
        ttl_seconds = 60

    class _Client:
        @staticmethod
        def fetch_profile(uid: str):
            return _Refused()

    monkeypatch.setattr(jobs_mod, "_try_import", lambda dotted: _Client)
    monkeypatch.setenv(jobs_mod.ENV_OFFLINE, "0")
    result = jobs_mod.sync_profile(jobs_mod.JobContext(uid="900000000"))
    assert result.failed
    assert result.message == _Refused.friendly_message


def test_sync_profile_skips_when_the_client_shape_is_unrecognised(monkeypatch) -> None:
    """Present but incompatible is a wiring gap, and a gap is a SKIP."""

    class _Unrecognised:
        pass

    monkeypatch.setattr(jobs_mod, "_try_import", lambda dotted: _Unrecognised)
    monkeypatch.setenv(jobs_mod.ENV_OFFLINE, "0")
    result = jobs_mod.sync_profile(jobs_mod.JobContext(uid="900000000"))
    assert result.skipped
    assert "fetch entrypoint" in result.message


def test_sync_profile_never_forces_a_refresh(monkeypatch) -> None:
    """Forcing would defeat the ttl suppression and burn rate limit."""
    seen: dict[str, object] = {}

    class _Profile:
        characters = ()
        ttl_seconds = 120

    class _Client:
        @staticmethod
        def fetch_profile(uid: str, **kwargs):
            seen.update(kwargs)
            return _Profile()

    monkeypatch.setattr(jobs_mod, "_try_import", lambda dotted: _Client)
    monkeypatch.setenv(jobs_mod.ENV_OFFLINE, "0")
    result = jobs_mod.sync_profile(jobs_mod.JobContext(uid="900000000"))
    assert result.ok, result.message
    assert seen.get("force") in (None, False)
    assert result.details["ttl_seconds"] == 120


def test_reconcile_state_skips_without_a_profile() -> None:
    """Live-state-first: with no current response there is nothing to derive."""
    result = jobs_mod.reconcile_state(jobs_mod.JobContext(uid="900000000"))
    assert result.skipped


def test_recompute_plan_skips_without_reconciled_state() -> None:
    result = jobs_mod.recompute_plan(jobs_mod.JobContext(uid="900000000"))
    assert result.skipped
    assert "state" in result.message


def test_recompute_plan_skips_when_no_goals_are_declared() -> None:
    from core.types import AccountState

    context = jobs_mod.JobContext(uid="900000000")
    context.state = AccountState(uid="900000000")
    result = jobs_mod.recompute_plan(context)
    assert result.skipped
    assert "goals" in result.message


def test_recompute_plan_solves_against_the_real_engines_api() -> None:
    """End to end against `engines`, not a stub.

    The planner exposes `build_graph` / `critical_path` / `plan`, verified by
    signature, and has NO single-argument `solve(state)`. A job wired to the
    latter would TypeError on every live pass, so this asserts the two-step it
    actually performs.
    """
    from core.types import AccountState, ObjectiveKind, ObjectiveNode

    ascend = ObjectiveNode(
        node_id="ascend_1",
        kind=ObjectiveKind.CHARACTER_ASCENSION,
        subject_id=10000096,
        target_value=1,
        resin_cost=60,
    )
    talent = ObjectiveNode(
        node_id="talent_1_6",
        kind=ObjectiveKind.TALENT_LEVEL,
        subject_id=10000096,
        target_value=6,
        depends_on=("ascend_1",),
        resin_cost=120,
    )
    context = jobs_mod.JobContext(uid="900000000")
    context.state = AccountState(uid="900000000", goals=(ascend, talent))

    result = jobs_mod.recompute_plan(context)
    assert result.ok, result.message
    assert result.details["path_count"] == 1

    path = context.options["resolution_paths"][0]
    # The prerequisite is ordered before the thing that needs it.
    assert path.ordered_nodes == ("ascend_1", "talent_1_6")
    assert path.total_resin == 180


def test_recompute_plan_skips_on_an_incompatible_planner(monkeypatch) -> None:
    """A shape mismatch is a wiring gap, reported SKIP rather than FAIL."""
    from core.types import AccountState, ObjectiveKind, ObjectiveNode

    class _Incompatible:
        pass

    node = ObjectiveNode(
        node_id="n", kind=ObjectiveKind.CHARACTER_LEVEL, subject_id=1, target_value=90
    )
    context = jobs_mod.JobContext(uid="900000000")
    context.state = AccountState(uid="900000000", goals=(node,))
    monkeypatch.setattr(jobs_mod, "_try_import", lambda dotted: _Incompatible)

    result = jobs_mod.recompute_plan(context)
    assert result.skipped
    assert "compatible planner entrypoint" in result.message


def test_recompute_plan_prefers_a_single_argument_entrypoint(monkeypatch) -> None:
    """If the planner grows `solve_goals(goals)`, that wins over the two-step."""
    from core.types import AccountState, ObjectiveKind, ObjectiveNode

    class _Modern:
        @staticmethod
        def solve_goals(goals):
            return ["one-shot path"]

        @staticmethod
        def build_graph(nodes):
            raise AssertionError("the two-step should not have been used")

    node = ObjectiveNode(
        node_id="n", kind=ObjectiveKind.CHARACTER_LEVEL, subject_id=1, target_value=90
    )
    context = jobs_mod.JobContext(uid="900000000")
    context.state = AccountState(uid="900000000", goals=(node,))
    monkeypatch.setattr(jobs_mod, "_try_import", lambda dotted: _Modern)

    result = jobs_mod.recompute_plan(context)
    assert result.ok, result.message
    assert context.options["resolution_paths"] == ["one-shot path"]


def test_accepts_one_positional_rejects_a_multi_argument_callable() -> None:
    """The guard that stops a two-argument planner being called with one."""

    def one(a):
        return a

    def two(a, b):
        return a

    def one_plus_defaults(a, b=1, *, c=2):
        return a

    assert jobs_mod._accepts_one_positional(one) is True
    assert jobs_mod._accepts_one_positional(two) is False
    assert jobs_mod._accepts_one_positional(one_plus_defaults) is True


def test_forecast_pity_skips_without_reconciled_state() -> None:
    result = jobs_mod.forecast_pity(jobs_mod.JobContext(uid="900000000"))
    assert result.skipped


def test_forecast_pity_records_a_forecast_from_the_real_engine() -> None:
    """End to end against `agents.pity_engine`, not a stub.

    Pins the call shape actually exported:
    `probability_of_success(state, target_count, pull_budget, banner=...)`.
    """
    from core.types import AccountState

    context = jobs_mod.JobContext(uid="900000000")
    context.state = AccountState(uid="900000000")
    context.options["target_count"] = 1
    context.options["pull_budget"] = 90

    result = jobs_mod.forecast_pity(context)
    if result.skipped:
        pytest.skip("the engine slice is not installed in this tree")

    assert result.ok, result.message
    probability = context.options["forecast"]
    # A full 90-pull budget from zero pity reaches hard pity, so a 5-star is
    # certain. Whether it is the RATE-UP one is not, which is why this is
    # below 1.0 rather than at it.
    assert 0.0 < probability < 1.0
    assert context.options["forecast_at"]


def test_forecast_pity_opens_no_socket_during_a_dry_run() -> None:
    """`allow_service_calls` is False under --dry-run, unconditionally."""
    assert jobs_mod.JobContext(dry_run=True).allow_service_calls is False
    assert jobs_mod.JobContext(dry_run=False).allow_service_calls is True


def test_emit_health_writes_the_heartbeat(tmp_path: Path) -> None:
    from ops import health as health_mod

    context = jobs_mod.JobContext(uid="900000000", dry_run=False, runtime_dir=str(tmp_path))
    result = jobs_mod.emit_health(context)
    assert result.ok, result.message
    assert (tmp_path / health_mod.HEALTH_FILENAME).is_file()
    assert health_mod.read_health(base=tmp_path)["role"] == "headless-runner"


def test_emit_health_writes_nothing_during_a_dry_run(tmp_path: Path) -> None:
    context = jobs_mod.JobContext(uid="900000000", dry_run=True, runtime_dir=str(tmp_path))
    result = jobs_mod.emit_health(context)
    assert result.skipped
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# run_job absorbs anything a job leaks
# ---------------------------------------------------------------------------


def test_run_job_converts_a_raising_job_into_a_fail(clean_registry) -> None:
    def _explode(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        raise RuntimeError("secret internal detail 0xdeadbeef")

    spec = jobs_mod.register(
        jobs_mod.JobSpec(name="explode", description="x", cadence="on_demand", func=_explode)
    )
    result = jobs_mod.run_job(spec, jobs_mod.JobContext())
    assert result.failed
    assert result.name == "explode"
    # The raw exception text stays in the log, not in the reported message.
    assert "0xdeadbeef" not in result.message
    assert result.details["error_type"] == "RuntimeError"


def test_run_job_rejects_a_job_that_returns_the_wrong_type(clean_registry) -> None:
    def _wrong(context: jobs_mod.JobContext):  # type: ignore[no-untyped-def]
        return "fine, thanks"

    spec = jobs_mod.register(
        jobs_mod.JobSpec(name="wrong_type", description="x", cadence="on_demand", func=_wrong)
    )
    result = jobs_mod.run_job(spec, jobs_mod.JobContext())
    assert result.failed
    assert "unexpected result type" in result.message


def test_run_job_records_a_duration(clean_registry) -> None:
    def _quick(context: jobs_mod.JobContext) -> jobs_mod.JobResult:
        return jobs_mod.passed("quick")

    spec = jobs_mod.register(
        jobs_mod.JobSpec(name="quick", description="x", cadence="on_demand", func=_quick)
    )
    result = jobs_mod.run_job(spec, jobs_mod.JobContext())
    assert result.duration_ms >= 0.0
    assert result.as_dict()["duration_ms"] >= 0.0


# ---------------------------------------------------------------------------
# JobResult
# ---------------------------------------------------------------------------


def test_the_three_statuses_are_mutually_exclusive() -> None:
    assert jobs_mod.passed("a").ok and not jobs_mod.passed("a").skipped
    assert jobs_mod.skipped("a", "why").skipped and not jobs_mod.skipped("a", "why").ok
    assert jobs_mod.failed("a", "why").failed and not jobs_mod.failed("a", "why").ok


def test_as_dict_carries_the_observable_contract() -> None:
    payload = jobs_mod.passed("a", "done").as_dict()
    assert set(payload) == {"name", "status", "ok", "skipped", "message", "duration_ms"}
    assert payload["status"] == "PASS"
