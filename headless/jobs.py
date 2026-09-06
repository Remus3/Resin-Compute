"""The headless job registry.

A job is one unit of reconciliation work. Jobs are registered declaratively
with `@job(...)`, ordered by their declared dependencies, and executed by
`headless.runner`.

Two rules govern every job in this file and they are not negotiable:

1. **No job may raise out of its own body.** A job answers with a `JobResult`
   in every case, including failure. The runner catches anyway - defence in
   depth, because a third-party job registered later cannot be trusted to keep
   this promise - but a job that leaks an exception is a defect here.
2. **A missing dependency is a SKIP, not a FAIL.** Sibling slices (`ingest`,
   `engines`, `agents.pity_engine`, `core.config`) may legitimately be absent:
   during parallel build, in a partial deployment, or in the CI smoke test.
   Absent is a known state that the pass reports and continues past. Only a
   dependency that is PRESENT and then misbehaves is a FAIL.

Both rules exist so that `python -m headless.runner --once --dry-run` exits 0
on a tree where nothing but this package has been built yet.

Sibling packages are imported LAZILY, inside the job body. A module-scope
import would couple import of the registry to the presence of every slice, and
one absent slice would then break the whole runner instead of one job.
"""
from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

#: Kill switch for every upstream fetch, modelled on Riot Commander's
#: `RC_DUO_SYNERGY_LIVE=0`. Set it to 1 and `sync_profile` SKIPs instead of
#: reaching the network. It is what lets a live (non-dry) pass be exercised in
#: a test or on a disconnected machine without inventing a fake transport, and
#: it exists because "--dry-run" and "do not touch the network" are different
#: requests: a dry run also declines to WRITE.
ENV_OFFLINE = "RESINCOMPUTE_OFFLINE"


def is_offline() -> bool:
    """True when upstream fetches are disabled by the environment."""
    return os.environ.get(ENV_OFFLINE, "").strip().lower() in {"1", "true", "yes", "on"}

# ---------------------------------------------------------------------------
# Cadence vocabulary
# ---------------------------------------------------------------------------
# Deliberately plain strings rather than `core.types.TaskCadence`. That enum
# describes how often a PLAYER-facing farming task may be performed (daily /
# weekly / on_demand); this describes how often a MACHINE job runs, and its
# dominant value is "every pass", which the domain enum has no member for.
# Borrowing the enum would force a wrong member onto four of the five jobs.
CADENCE_PER_PASS = "per_pass"
CADENCE_DAILY = "daily"
CADENCE_WEEKLY = "weekly"
CADENCE_ON_DEMAND = "on_demand"

# Job outcome vocabulary. These exact strings are what the runner logs and what
# lands in `ops/runtime/health.json`, so they are part of the observable
# contract, not an implementation detail.
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIP = "SKIP"


# ---------------------------------------------------------------------------
# Result + context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JobResult:
    """The small result object every job returns.

    `ok` and `skipped` are kept as separate booleans rather than being derived
    from `status`, because the three states are not a two-valued question: a
    skipped job is neither a success to celebrate nor a failure to alert on,
    and collapsing it into either one is how a monitor starts lying.
    """

    name: str
    status: str = STATUS_PASS
    message: str = ""
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == STATUS_PASS

    @property
    def skipped(self) -> bool:
        return self.status == STATUS_SKIP

    @property
    def failed(self) -> bool:
        return self.status == STATUS_FAIL

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "ok": self.ok,
            "skipped": self.skipped,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 3),
        }


def passed(name: str, message: str = "", **details: Any) -> JobResult:
    return JobResult(name=name, status=STATUS_PASS, message=message, details=details)


def skipped(name: str, message: str, **details: Any) -> JobResult:
    return JobResult(name=name, status=STATUS_SKIP, message=message, details=details)


def failed(name: str, message: str, **details: Any) -> JobResult:
    return JobResult(name=name, status=STATUS_FAIL, message=message, details=details)


@dataclass
class JobContext:
    """Everything a job is allowed to read from the outside world.

    Passing a context rather than letting jobs reach for globals is what makes
    the registry testable: a test constructs a context with `dry_run=True` and
    a temp runtime dir and nothing touches the real tree.

    `state` is the reconciliation target, threaded from job to job. It starts
    as None and `reconcile_state` populates it - which is why `recompute_plan`
    and `forecast_pity` declare a dependency on that job rather than rebuilding
    the state themselves.
    """

    uid: str | None = None
    dry_run: bool = False
    runtime_dir: str | None = None
    started_at: str = ""
    state: Any = None
    profile: Any = None
    results: dict[str, JobResult] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def allow_service_calls(self) -> bool:
        """Whether a job may open a loopback socket to a local service.

        False under `--dry-run`, unconditionally. The CI smoke test runs
        `--once --dry-run` in a sandbox with no network, so a dry run that
        probed a socket would make the smoke test's exit code depend on the
        sandbox's socket behaviour.
        """
        return not self.dry_run and bool(self.options.get("allow_service_calls", True))


JobFunc = Callable[[JobContext], JobResult]


@dataclass(frozen=True)
class JobSpec:
    """One registered job."""

    name: str
    description: str
    cadence: str
    func: JobFunc
    depends_on: tuple[str, ...] = ()
    #: Registration sequence number. This is what makes the order
    #: DETERMINISTIC rather than merely topological: several orderings satisfy
    #: the dependency graph, and ties are broken by declaration order so two
    #: runs of the same build always emit the same sequence.
    sequence: int = 0


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, JobSpec] = {}
_SEQUENCE = 0


def job(
    name: str,
    description: str = "",
    cadence: str = CADENCE_PER_PASS,
    depends_on: tuple[str, ...] = (),
) -> Callable[[JobFunc], JobFunc]:
    """Register a job function under `name`.

    The decorated function is returned unchanged, so it stays directly callable
    in a test without going through the registry.
    """

    def decorator(func: JobFunc) -> JobFunc:
        register(
            JobSpec(
                name=name,
                description=description or _first_docstring_line(func),
                cadence=cadence,
                func=func,
                depends_on=tuple(depends_on),
            )
        )
        return func

    return decorator


def _first_docstring_line(func: JobFunc) -> str:
    """Summary line of a function's docstring, or an empty string."""
    lines = (func.__doc__ or "").strip().splitlines()
    return lines[0].strip() if lines else ""


def register(spec: JobSpec) -> JobSpec:
    """Insert a spec into the registry, stamping its sequence number."""
    global _SEQUENCE
    if spec.name in _REGISTRY:
        raise ValueError(f"duplicate job name: {spec.name}")
    _SEQUENCE += 1
    stamped = JobSpec(
        name=spec.name,
        description=spec.description,
        cadence=spec.cadence,
        func=spec.func,
        depends_on=spec.depends_on,
        sequence=_SEQUENCE,
    )
    _REGISTRY[spec.name] = stamped
    return stamped


def unregister(name: str) -> None:
    """Remove a job. Missing name is a no-op, so teardown is idempotent."""
    _REGISTRY.pop(name, None)


def registry_snapshot() -> dict[str, JobSpec]:
    """Shallow copy of the registry, for a test to restore afterwards."""
    return dict(_REGISTRY)


def restore_registry(snapshot: dict[str, JobSpec]) -> None:
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)


def get_job(name: str) -> JobSpec | None:
    return _REGISTRY.get(name)


def job_names() -> list[str]:
    return [spec.name for spec in ordered_jobs()]


def ordered_jobs() -> list[JobSpec]:
    """Every registered job in dependency order.

    Stable topological sort: at each step, of the jobs whose dependencies are
    already satisfied, take the one with the lowest registration sequence. That
    makes the output a pure function of the registry contents - the same set of
    jobs always yields the same order, on every run and every platform.

    A dependency naming an unregistered job is IGNORED rather than fatal. A job
    may legitimately depend on one that a deployment has not installed, and
    refusing to run the whole pass over it would be a worse failure than
    running the rest.

    A dependency cycle cannot deadlock the pass: once no candidate is
    satisfiable the remaining jobs are emitted in sequence order and the cycle
    is logged.
    """
    remaining = sorted(_REGISTRY.values(), key=lambda s: s.sequence)
    known = set(_REGISTRY)
    done: set[str] = set()
    out: list[JobSpec] = []

    while remaining:
        ready = [s for s in remaining if all(d in done or d not in known for d in s.depends_on)]
        if not ready:
            names = ", ".join(s.name for s in remaining)
            log.warning("job dependency cycle detected, emitting in declaration order: %s", names)
            out.extend(remaining)
            break
        head = ready[0]
        out.append(head)
        done.add(head.name)
        remaining.remove(head)
    return out


def run_job(spec: JobSpec, context: JobContext) -> JobResult:
    """Execute one job, timing it and absorbing any exception it leaks.

    A job that raises is reported FAIL with a friendly message. The raw
    exception goes to the log only - the inherited rule is that a raw error
    string never reaches a user-facing surface, and `health.json` is one.
    """
    start = time.perf_counter()
    try:
        result = spec.func(context)
    except Exception as exc:  # noqa: BLE001 - a job MUST NOT abort the pass
        log.exception("job %s raised", spec.name)
        elapsed = (time.perf_counter() - start) * 1000.0
        return JobResult(
            name=spec.name,
            status=STATUS_FAIL,
            message="job raised an unexpected error - see the log",
            duration_ms=elapsed,
            details={"error_type": type(exc).__name__},
        )
    elapsed = (time.perf_counter() - start) * 1000.0
    if not isinstance(result, JobResult):
        log.error("job %s returned %s, expected JobResult", spec.name, type(result).__name__)
        return JobResult(
            name=spec.name,
            status=STATUS_FAIL,
            message="job returned an unexpected result type",
            duration_ms=elapsed,
        )
    return JobResult(
        name=result.name or spec.name,
        status=result.status,
        message=result.message,
        duration_ms=elapsed,
        details=result.details,
    )


# ---------------------------------------------------------------------------
# Optional-dependency helper
# ---------------------------------------------------------------------------


def _try_import(dotted: str) -> Any | None:
    """Import a module by dotted path, answering None when it is absent.

    Only ImportError is swallowed. A module that exists but explodes on import
    is a real defect and must surface as a FAIL, not be disguised as a missing
    slice.
    """
    import importlib

    try:
        return importlib.import_module(dotted)
    except ImportError as exc:
        log.debug("optional dependency %s unavailable: %s", dotted, exc)
        return None


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# The jobs
# ---------------------------------------------------------------------------


@job(
    name="sync_profile",
    description="Refresh the account roster through the upstream profile client.",
    cadence=CADENCE_PER_PASS,
)
def sync_profile(context: JobContext) -> JobResult:
    """Fetch the profile, honouring the upstream ttl cache.

    The ttl is not advisory. Per the Enka policy recorded in SPEC_SCAFFOLD
    section 4, cached data is served until `ttl` expires and a request inside
    that window STILL burns the rate limit, so the client suppresses requests
    rather than the server doing it for us. That suppression lives in the
    client; this job only has to not defeat it, which means never passing a
    force-refresh flag from a routine pass.
    """
    name = "sync_profile"
    if not context.uid:
        return skipped(name, "no uid configured - pass --uid or set RESINCOMPUTE_UID")

    client_mod = _try_import("ingest.enka_client")
    if client_mod is None:
        return skipped(name, "ingest.enka_client is not installed")

    if context.dry_run:
        return skipped(name, f"dry run - would fetch profile for uid {context.uid}")

    if is_offline():
        return skipped(name, f"offline mode - set {ENV_OFFLINE}=0 to allow upstream fetches")

    try:
        profile, ttl = _fetch_mapped_profile(client_mod, context.uid)
    except _UpstreamRefused as exc:
        # The client already produced an operator-safe sentence. Passing it
        # through is the ONE place a message from below is allowed out, and
        # only because the ingest slice built it for that purpose.
        return failed(name, str(exc))
    except _ClientShapeError as exc:
        log.warning("sync_profile found no usable client entrypoint: %s", exc)
        return skipped(name, "ingest.enka_client exposes no fetch entrypoint")
    except Exception as exc:  # noqa: BLE001 - a job MUST NOT abort the pass
        log.exception("sync_profile failed for uid %s", context.uid)
        return failed(name, "profile fetch failed - see the log", error_type=type(exc).__name__)

    context.profile = profile
    characters = getattr(profile, "characters", ()) or ()
    return passed(
        name,
        f"profile refreshed - {len(characters)} roster entries, ttl {ttl}",
        roster_size=len(characters),
        ttl_seconds=ttl,
    )


class _ClientShapeError(RuntimeError):
    """The ingest slice is present but exposes nothing this job can call."""


class _UpstreamRefused(RuntimeError):
    """The upstream declined. Carries the client's own friendly message."""


def _fetch_mapped_profile(client_mod: Any, uid: str) -> tuple[Any, Any]:
    """Fetch and map one profile. Returns `(profile, ttl_seconds)`.

    Wired against the ingest API as it actually exists, verified by
    `inspect.signature`:

        EnkaClient(EnkaConfig(user_agent=...)).fetch_profile(uid) -> FetchResult
        ingest.map_profile(payload, uid=...) -> EnkaMappedProfile

    `force` is never passed. The client suppresses requests until the response
    `ttl` expires, and a routine pass that forced a refresh would defeat that
    and burn rate limit for data it already holds.

    A module-level `fetch_profile` / `fetch` is probed first so a later
    refactor of the ingest slice into free functions does not break this job.
    """
    module_level = getattr(client_mod, "fetch_profile", None) or getattr(client_mod, "fetch", None)
    if callable(module_level) and not isinstance(module_level, type):
        result = module_level(uid)
        return _unwrap_fetch_result(result, uid)

    client_cls = getattr(client_mod, "EnkaClient", None)
    config_cls = getattr(client_mod, "EnkaConfig", None)
    if client_cls is None or config_cls is None:
        raise _ClientShapeError("neither a fetch function nor EnkaClient/EnkaConfig is available")

    client = client_cls(config=config_cls(user_agent=_configured_user_agent()))
    return _unwrap_fetch_result(client.fetch_profile(uid), uid)


def _unwrap_fetch_result(result: Any, uid: str) -> tuple[Any, Any]:
    """Turn whatever the client returned into `(mapped profile, ttl)`."""
    # Already a mapped profile: it carries a roster rather than raw JSON.
    if hasattr(result, "characters"):
        return result, getattr(result, "ttl_seconds", None)

    if hasattr(result, "ok") and not result.ok:
        raise _UpstreamRefused(
            getattr(result, "friendly_message", "") or "the profile service declined the request"
        )

    payload = getattr(result, "profile_json", None)
    if payload is None:
        raise _ClientShapeError("the fetch result carried no profile payload")

    ingest_pkg = _try_import("ingest")
    map_profile = getattr(ingest_pkg, "map_profile", None) if ingest_pkg else None
    if not callable(map_profile):
        raise _ClientShapeError("ingest exposes no map_profile")
    return map_profile(payload, uid=uid), getattr(result, "ttl_seconds", None)


def _configured_user_agent() -> str:
    """The custom User-Agent upstream policy REQUIRES on every request.

    Sourced from `core.config` when that slice is present, because the operator
    is expected to override the default with a contactable value there. An
    empty string is never sent: the client rejects it, which is the correct
    behaviour and not something this job should route around.
    """
    config_mod = _try_import("core.config")
    load_config = getattr(config_mod, "load_config", None) if config_mod else None
    if callable(load_config):
        config = load_config()
        agent = getattr(config, "enka_user_agent", "")
        if agent:
            return str(agent)
    return ""


@job(
    name="reconcile_state",
    description="Recompute the account aggregate from the current response only.",
    cadence=CADENCE_PER_PASS,
    depends_on=("sync_profile",),
)
def reconcile_state(context: JobContext) -> JobResult:
    """Rebuild `AccountState` from the freshly fetched profile.

    LIVE-STATE-FIRST, which is the whole point of this job. State is derived
    from the CURRENT response and nothing else. A previously reconciled
    aggregate is never carried forward as truth and no roster is hardcoded, so
    a character removed from the showcase disappears from the state rather than
    lingering because a cache still remembers it.

    An absent showcase is a real, ordinary upstream state: `avatarInfoList` is
    omitted entirely rather than sent empty, so an empty roster here is not
    evidence of a failed fetch.
    """
    name = "reconcile_state"
    if not context.uid:
        return skipped(name, "no uid configured - nothing to reconcile")

    types_mod = _try_import("core.types")
    if types_mod is None:
        return skipped(name, "core.types is not installed")

    account_cls = getattr(types_mod, "AccountState", None)
    if account_cls is None:
        return skipped(name, "core.types exposes no AccountState")

    profile = context.profile
    if profile is None:
        return skipped(name, "no profile in this pass - sync_profile did not produce one")

    if context.dry_run:
        return skipped(name, "dry run - would rebuild the account aggregate")

    try:
        roster = tuple(getattr(profile, "characters", ()) or ())
        state = account_cls(
            uid=str(getattr(profile, "uid", context.uid)),
            adventure_rank=int(getattr(profile, "adventure_rank", 0) or 0),
            world_level=int(getattr(profile, "world_level", 0) or 0),
            roster=roster,
        )
        state.last_synced_at = getattr(profile, "fetched_at", None)
    except Exception as exc:  # noqa: BLE001 - a job MUST NOT abort the pass
        log.exception("reconcile_state failed for uid %s", context.uid)
        return failed(name, "state reconciliation failed - see the log", error_type=type(exc).__name__)

    context.state = state
    return passed(name, f"state rebuilt from the live response - {len(roster)} roster entries",
                  roster_size=len(roster))


@job(
    name="recompute_plan",
    description="Re-solve the objective DAG and the task scheduler.",
    cadence=CADENCE_DAILY,
    depends_on=("reconcile_state",),
)
def recompute_plan(context: JobContext) -> JobResult:
    """Re-solve the goal graph for the account's declared objectives.

    Wired against the engines API as it actually exists, verified by
    `inspect.signature` rather than assumed:

        engines.build_graph(nodes)            -> ObjectiveGraph
        engines.critical_path(nodes, goal_id) -> ResolutionPath
        engines.plan(path, nodes, resin_per_day=...) -> ResolutionPath

    There is no single `solve(state)` entrypoint, so this job does the two-step
    itself. A GOAL is a node nothing else depends on - a leaf of the dependency
    DAG - because an interior node is a prerequisite of something rather than an
    end in itself. That interpretation belongs to the headless lane, not to the
    planner, which is why it is stated here in one place.

    If the planner slice ever grows a single-argument `solve_goals(state)` or
    `resolve(state)`, that is preferred and this two-step becomes the fallback.
    """
    name = "recompute_plan"
    state = context.state
    if state is None:
        return skipped(name, "no reconciled state in this pass - nothing to plan against")

    planner = _try_import("engines")
    if planner is None:
        return skipped(name, "engines is not installed")

    goals = tuple(getattr(state, "goals", ()) or ())
    if not goals:
        return skipped(name, "no goals declared for this account")

    if context.dry_run:
        return skipped(name, f"dry run - would solve {len(goals)} objectives")

    resin_per_day = int(getattr(getattr(state, "velocity", None), "resin_per_day", 180) or 180)

    try:
        paths = _solve_goal_paths(planner, goals, resin_per_day)
    except _PlannerShapeError as exc:
        # A shape mismatch is a WIRING gap, not a runtime fault. Reporting it
        # as FAIL would page someone about a contract that was never agreed.
        log.warning("recompute_plan found no compatible planner entrypoint: %s", exc)
        return skipped(name, "engines exposes no compatible planner entrypoint")
    except Exception as exc:  # noqa: BLE001 - a job MUST NOT abort the pass
        log.exception("recompute_plan failed for uid %s", context.uid)
        return failed(name, "planning failed - see the log", error_type=type(exc).__name__)

    context.options["resolution_paths"] = paths
    return passed(name, f"plan re-solved - {len(paths)} resolution paths", path_count=len(paths))


class _PlannerShapeError(RuntimeError):
    """The planner is present but its entrypoints do not match what we call."""


def _accepts_one_positional(func: Any) -> bool:
    """True when `func` can be called with exactly one positional argument.

    Guards the preferred single-argument path. Calling a two-argument planner
    with one argument would raise a TypeError that reads as a runtime failure
    when it is really a contract mismatch.
    """
    import inspect

    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return False
    required = [
        p
        for p in signature.parameters.values()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty
    ]
    return len(required) == 1


def _solve_goal_paths(planner: Any, goals: tuple[Any, ...], resin_per_day: int) -> list[Any]:
    """Resolve every goal to a scheduled path. Raises `_PlannerShapeError`."""
    for entrypoint in ("solve_goals", "resolve"):
        candidate = getattr(planner, entrypoint, None)
        if callable(candidate) and _accepts_one_positional(candidate):
            result = candidate(goals)
            return list(result) if hasattr(result, "__iter__") else [result]

    build_graph = getattr(planner, "build_graph", None)
    critical_path = getattr(planner, "critical_path", None)
    plan = getattr(planner, "plan", None)
    if not all(callable(f) for f in (build_graph, critical_path, plan)):
        raise _PlannerShapeError("build_graph / critical_path / plan are not all available")

    graph = build_graph(goals)
    leaves = [node.node_id for node in goals if not graph.dependents_of(node.node_id)]
    return [plan(critical_path(goals, leaf), goals, resin_per_day=resin_per_day) for leaf in leaves]


@job(
    name="forecast_pity",
    description="Record a wish forecast from the compute engine.",
    cadence=CADENCE_DAILY,
    depends_on=("reconcile_state",),
)
def forecast_pity(context: JobContext) -> JobResult:
    """Forecast success probability through the compute engine.

    Calls the engine LIBRARY in-process. `agents.pity_engine` is a pure,
    deterministic function of its inputs, so the library and the `:8790`
    service compute the identical answer - and the library needs no socket, no
    running daemon and no serialisation round trip. The service exists for
    callers OUTSIDE this process; a job that runs inside the same interpreter
    has no reason to go over a socket to reach it.

    `context.allow_service_calls` is the gate a future HTTP path must consult:
    it is False under `--dry-run`, unconditionally, so the CI smoke test opens
    no socket. Today the job returns before that point, because a dry run has
    nothing to record.
    """
    name = "forecast_pity"
    state = context.state
    if state is None:
        return skipped(name, "no reconciled state in this pass - nothing to forecast")

    if context.dry_run:
        return skipped(name, "dry run - would query the compute engine")

    engine = _try_import("agents.pity_engine")
    if engine is None:
        return skipped(name, "agents.pity_engine is not installed")

    probability_of_success = getattr(engine, "probability_of_success", None)
    if not callable(probability_of_success):
        return skipped(name, "agents.pity_engine exposes no forecast entrypoint")

    target = context.options.get("target_count", 1)
    budget = context.options.get("pull_budget", 90)
    try:
        pity_state = state.pity_for(_default_banner(engine))
        answer = probability_of_success(pity_state, int(target), int(budget))
    except Exception as exc:  # noqa: BLE001 - a job MUST NOT abort the pass
        log.exception("forecast_pity failed for uid %s", context.uid)
        return failed(name, "forecast failed - see the log", error_type=type(exc).__name__)

    # MEASURED, not assumed: the engine returns a `ForecastResult`, whose
    # `probability` is the scalar. SPEC_SCAFFOLD section 3.8 writes the
    # signature as `-> float`; the shipped engine returns the richer object so
    # a caller can render a distribution without a second solve. Both shapes
    # are accepted here rather than pinning one, because this job is the
    # consumer and neither slice owns the other's return type.
    probability = getattr(answer, "probability", answer)
    try:
        probability = float(probability)
    except (TypeError, ValueError):
        log.error("forecast returned %s, which is not a probability", type(answer).__name__)
        return failed(name, "forecast returned an unexpected result type")

    context.options["forecast"] = probability
    context.options["forecast_result"] = answer
    context.options["forecast_at"] = _utc_now_iso()
    return passed(
        name,
        f"forecast recorded - p={probability:.4f} over {budget} pulls",
        probability=probability,
        pull_budget=budget,
    )


def _default_banner(engine: Any) -> Any:
    """The banner family a routine forecast defaults to.

    Character Event Wish, because it is the only family Capturing Radiance
    applies to and therefore the only one whose forecast is wrong if you model
    it as a flat 50/50. Falls back to whatever the engine hands back for a
    default when the enum cannot be imported.
    """
    types_mod = _try_import("core.types")
    banner_kind = getattr(types_mod, "BannerKind", None) if types_mod else None
    if banner_kind is not None:
        return banner_kind.CHARACTER_EVENT
    return getattr(engine, "DEFAULT_BANNER", None)


@job(
    name="emit_health",
    description="Write the heartbeat to the runtime health file.",
    cadence=CADENCE_PER_PASS,
    depends_on=("reconcile_state", "recompute_plan", "forecast_pity"),
)
def emit_health(context: JobContext) -> JobResult:
    """Write the heartbeat.

    Runs LAST so the file it writes reflects the pass that produced it. The
    runner writes the authoritative pass summary itself after every job has
    reported; this job is the in-pass heartbeat, which matters in daemon mode
    where a long pass would otherwise look stale to a watchdog for its whole
    duration.
    """
    name = "emit_health"
    if context.dry_run:
        return skipped(name, "dry run - would write the heartbeat")

    from ops import health

    try:
        path = health.write_health(
            alive=True,
            started_at=context.started_at or None,
            uid=context.uid,
            role="headless-runner",
            message="pass in progress",
            jobs=[r.as_dict() for r in context.results.values()],
            engine_version_value=health.engine_version(),
            base=Path(context.runtime_dir) if context.runtime_dir else None,
        )
    except OSError as exc:
        log.exception("emit_health could not write the heartbeat")
        return failed(name, "could not write the heartbeat - see the log", error_type=type(exc).__name__)

    return passed(name, f"heartbeat written to {path}")
