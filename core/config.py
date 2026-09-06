"""Live-state-first configuration for ResinCompute.

Every value is derived from the CURRENT process environment on each call to
`load_config()`. There is deliberately NO module-level cached `Config` object:
a cached value that disagrees with the environment is a stale cache pretending
to be truth, which is exactly the failure the live-state-first rule in
docs/SPEC_SCAFFOLD.md section 2 exists to prevent. Callers that want a snapshot
hold the returned frozen dataclass themselves.

No account UID appears anywhere in this module. A UID is caller-supplied input,
never configuration baked into the tree.

This module imports `logging` directly rather than `core.log_setup`, because
`core.log_setup` reads its log directory from here. Importing the other way
would close a cycle. Nothing here configures the root logger.

Environment variables - all optional, defaults documented:

    RESIN_ENGINE_HOST      default "127.0.0.1"
        Bind / connect host for the PityEngine HTTP service.
    RESIN_ENGINE_PORT      default 8870
        Its port. SPEC_SCAFFOLD section 1 pins the engine to :8870, mirroring
        Riot Commander's Daemon Slayer on :8860.
    RC_DATA_DIR            default "<repo>/data"
        Root for hand-authored fixtures and the runtime fetch cache.
    RC_LOG_DIR             default "<repo>/logs"
        Holds one log file per day, no rotation.
    ENKA_USER_AGENT        default DEFAULT_ENKA_USER_AGENT
        REQUIRED BY UPSTREAM POLICY (SPEC_SCAFFOLD section 4): the Enka docs
        state a custom User-Agent is mandatory. The built-in default is a
        placeholder that identifies the software but not the operator, so
        `user_agent_is_default` is exposed and a caller can warn on it.
    ENKA_BASE_URL          default "https://enka.network"
        Upstream origin. The brief's "https://enka.network<uid>" is malformed;
        the real paths are "/api/uid/{uid}/" and "/api/uid/{uid}/?info".
    ENKA_TIMEOUT_SECONDS   default 15
        Per-request timeout in seconds.
    RESIN_LOG_LEVEL        default "INFO"
        Level applied to both the console and file handlers.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

# Repo root. Mirrors Riot Commander's hard rule that SCRIPT_DIR is derived from
# __file__ and never from the process working directory: core/config.py -> core
# -> repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_ENGINE_HOST = "127.0.0.1"
DEFAULT_ENGINE_PORT = 8870
DEFAULT_ENKA_BASE_URL = "https://enka.network"
DEFAULT_ENKA_TIMEOUT_SECONDS = 15
DEFAULT_LOG_LEVEL = "INFO"

# Placeholder User-Agent. Upstream policy requires a CUSTOM one, so an operator
# is expected to override this via ENKA_USER_AGENT with a contactable value.
DEFAULT_ENKA_USER_AGENT = "ResinCompute/0.1 (local single-account planner)"


@dataclass(frozen=True)
class Config:
    """One immutable snapshot of the environment.

    Frozen so a consumer cannot mutate shared configuration behind another
    consumer's back. New fields are APPENDED with defaults, per the dataclass
    convention inherited from Riot Commander.
    """

    engine_host: str = DEFAULT_ENGINE_HOST
    engine_port: int = DEFAULT_ENGINE_PORT
    data_dir: Path = REPO_ROOT / "data"
    log_dir: Path = REPO_ROOT / "logs"
    enka_user_agent: str = DEFAULT_ENKA_USER_AGENT
    enka_base_url: str = DEFAULT_ENKA_BASE_URL
    enka_timeout_seconds: int = DEFAULT_ENKA_TIMEOUT_SECONDS
    log_level: str = DEFAULT_LOG_LEVEL
    user_agent_is_default: bool = True

    @property
    def engine_url(self) -> str:
        """Base URL of the local PityEngine service."""
        return f"http://{self.engine_host}:{self.engine_port}"

    def uid_endpoint(self, uid: str, info_only: bool = False) -> str:
        """Return the verified Enka endpoint for one UID.

        Shapes are pinned by SPEC_SCAFFOLD section 5. `info_only` selects the
        much faster playerInfo-only variant.
        """
        base = f"{self.enka_base_url.rstrip('/')}/api/uid/{uid}/"
        return base + "?info" if info_only else base


def _env_str(name: str, default: str) -> str:
    """Read a string env var. An empty or whitespace-only value means unset."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip()


def _env_int(name: str, default: int) -> int:
    """Read an integer env var, degrading to the default on garbage.

    Never raises and never surfaces the raw parse error to the caller: a typo
    in an environment variable must not take the process down.
    """
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        _log.warning("config: %s=%r is not an integer, using default %d", name, raw, default)
        return default


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return Path(raw.strip()).expanduser()


def load_config() -> Config:
    """Build a Config from the environment as it is RIGHT NOW.

    Called on every use rather than once at import. Cheap - a handful of dict
    lookups - and it is what makes a test able to set an env var and observe the
    effect without reloading the module.
    """
    user_agent = _env_str("ENKA_USER_AGENT", DEFAULT_ENKA_USER_AGENT)
    return Config(
        engine_host=_env_str("RESIN_ENGINE_HOST", DEFAULT_ENGINE_HOST),
        engine_port=_env_int("RESIN_ENGINE_PORT", DEFAULT_ENGINE_PORT),
        data_dir=_env_path("RC_DATA_DIR", REPO_ROOT / "data"),
        log_dir=_env_path("RC_LOG_DIR", REPO_ROOT / "logs"),
        enka_user_agent=user_agent,
        enka_base_url=_env_str("ENKA_BASE_URL", DEFAULT_ENKA_BASE_URL),
        enka_timeout_seconds=_env_int("ENKA_TIMEOUT_SECONDS", DEFAULT_ENKA_TIMEOUT_SECONDS),
        log_level=_env_str("RESIN_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
        user_agent_is_default=(user_agent == DEFAULT_ENKA_USER_AGENT),
    )
