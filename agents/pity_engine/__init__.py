"""PityEngine - local gacha forecasting engine.

Absorbing-Markov-chain forecasting over the joint state `(copies, pity,
guarantee, consecutive 50/50 losses)`, layered on hazard tables that COMPUTE
their own hard pity from the ramp rather than declaring it alongside one, plus
the Capturing Radiance branch model that replaced the flat 50/50 in version 5.0.
Pure and deterministic: no clock, no randomness, no I/O and no global state, so
identical arguments always return identical floats. New capability is added as
an opt-in argument that is byte-identical to the prior version at its default.

`ENGINE_VERSION` below is the single source of truth for the engine revision.
The full per-version history lives in `CHANGELOG.md` beside this file. Future
bumps PREPEND a new entry there and never extend a prior version's line.

The engine is exposed over local HTTP on port 8870 (`python -m
agents.pity_engine`), mirroring how Riot Commander exposes Daemon Slayer on
8860. Nothing in the compute path knows the transport exists.

Every domain constant traces to `docs/SPEC_SCAFFOLD.md` section 3. Three
corrections to the original brief are load-bearing and are guarded by tests:
Capturing Radiance replaces the flat 50/50, the weapon curve saturates at pity
77 rather than the briefed 79/80, and a forecast needs an explicit pull budget.
"""

ENGINE_VERSION = "0.1.0"

from .banners import (  # noqa: E402
    CAPTURING_RADIANCE_CAP,
    CAPTURING_RADIANCE_P,
    CHARACTER_FIVE_STAR_TABLE,
    CHRONICLED_DESIGNATED_P,
    FIVE_STAR_INCREMENT_WEAPON_DEFAULT,
    FOUR_STAR_TABLE_CHARACTER,
    FOUR_STAR_TABLE_WEAPON,
    WEAPON_FEATURED_SINGLE_P,
    WEAPON_FIVE_STAR_TABLE,
    BannerConfig,
    banner_config,
    build_five_star_table,
    capturing_radiance_long_run_rate,
    character_five_star_table,
    character_rate_up,
    chronicled_rate_up,
    effective_hard_pity,
    standard_rate_up,
    weapon_five_star_table,
    weapon_rate_up,
)
from .forecast import probability_of_success, pulls_needed_for_confidence  # noqa: E402
from .markov import (  # noqa: E402
    ChainSolution,
    consolidated_rate,
    expected_wishes_per_five_star,
    pull_distribution,
    solve,
)

__all__ = [
    "CAPTURING_RADIANCE_CAP",
    "CAPTURING_RADIANCE_P",
    "CHARACTER_FIVE_STAR_TABLE",
    "CHRONICLED_DESIGNATED_P",
    "ENGINE_VERSION",
    "FIVE_STAR_INCREMENT_WEAPON_DEFAULT",
    "FOUR_STAR_TABLE_CHARACTER",
    "FOUR_STAR_TABLE_WEAPON",
    "WEAPON_FEATURED_SINGLE_P",
    "WEAPON_FIVE_STAR_TABLE",
    "BannerConfig",
    "ChainSolution",
    "banner_config",
    "build_five_star_table",
    "capturing_radiance_long_run_rate",
    "character_five_star_table",
    "character_rate_up",
    "chronicled_rate_up",
    "consolidated_rate",
    "effective_hard_pity",
    "expected_wishes_per_five_star",
    "probability_of_success",
    "pull_distribution",
    "pulls_needed_for_confidence",
    "solve",
    "standard_rate_up",
    "weapon_five_star_table",
    "weapon_rate_up",
]
