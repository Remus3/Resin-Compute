"""ResinCompute shared type contract.

This module is the merge surface between every engine slice. It is written once,
before fan-out, and is READ-ONLY to build slices - a slice that needs a new field
asks for it rather than editing this file, so parallel slices cannot conflict
here.

Convention inherited from Riot Commander: when a required field is added to a
dataclass it is appended at the END with a default. A mid-class required field
breaks every existing positional construction and its tests.

All identifiers are domain-neutral. Game-specific proper nouns appear only as
data values, never as type or field names.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class BannerKind(StrEnum):
    """Wish banner families.

    Each family carries its OWN independent pity counter. Character Event Wish
    and Character Event Wish-2 deliberately share one counter, so they map to a
    single member here rather than two.
    """

    CHARACTER_EVENT = "character_event"
    WEAPON_EVENT = "weapon_event"
    STANDARD = "standard"
    CHRONICLED = "chronicled"


class CurrencyKind(StrEnum):
    """Every balance the ledger tracks.

    Resin variants are separate members because they obey different rules:
    ORIGINAL_RESIN regenerates on a wall-clock timer and caps, FRAGILE_RESIN is
    an inventory item that grants 60 on use, and CONDENSED_RESIN is a crafted
    item that spends 40 to double a single domain payout.
    """

    PRIMOGEM = "primogem"
    INTERTWINED_FATE = "intertwined_fate"
    ACQUAINT_FATE = "acquaint_fate"
    STARDUST = "masterless_stardust"
    STARGLITTER = "masterless_starglitter"
    MORA = "mora"
    ORIGINAL_RESIN = "original_resin"
    FRAGILE_RESIN = "fragile_resin"
    CONDENSED_RESIN = "condensed_resin"
    HEROS_WIT = "heros_wit"


class Element(StrEnum):
    PYRO = "pyro"
    HYDRO = "hydro"
    ANEMO = "anemo"
    ELECTRO = "electro"
    DENDRO = "dendro"
    CRYO = "cryo"
    GEO = "geo"


class EquipItemType(StrEnum):
    """Mirrors the Enka wire values exactly.

    These two strings are the literal `flat.itemType` values in the upstream
    payload. Do not rename the values; the mapper compares against them.
    """

    RELIQUARY = "ITEM_RELIQUARY"
    WEAPON = "ITEM_WEAPON"


class ObjectiveKind(StrEnum):
    """The atomic goal types the planner DAG can express."""

    CHARACTER_ASCENSION = "character_ascension"
    CHARACTER_LEVEL = "character_level"
    TALENT_LEVEL = "talent_level"
    WEAPON_ASCENSION = "weapon_ascension"
    WEAPON_LEVEL = "weapon_level"
    ACQUIRE_CHARACTER = "acquire_character"
    ACQUIRE_WEAPON = "acquire_weapon"


class TaskCadence(StrEnum):
    """How often a scheduled task may be executed."""

    DAILY = "daily"
    WEEKLY = "weekly"
    ON_DEMAND = "on_demand"


# ---------------------------------------------------------------------------
# Gacha state
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PityState:
    """Complete gacha state for ONE banner family.

    The brief's `PityStats {currentPity, hasGuarantee, fatesAvailable}` is
    insufficient for a correct forecast on two counts, both recorded in
    docs/SPEC_SCAFFOLD.md section 3:

    1. `consecutive_5050_losses` is required because Capturing Radiance
       (version 5.0) caps consecutive 50/50 losses at three. Without it the
       forecaster cannot express the forced win.
    2. `fates_available` is a WALLET quantity, not a pity quantity. It belongs
       on the ledger, not here. `fate_points` on this dataclass is the weapon
       banner Epitomized Path counter, which is a different thing entirely and
       is capped at 1 since version 5.0.

    `pity_5star` and `pity_4star` are counts of wishes made SINCE the last
    payout of that rarity, so a fresh account is 0 on both.
    """

    banner: BannerKind = BannerKind.CHARACTER_EVENT
    pity_5star: int = 0
    pity_4star: int = 0
    has_guarantee: bool = False
    consecutive_5050_losses: int = 0
    fate_points: int = 0

    def __post_init__(self) -> None:
        if self.pity_5star < 0 or self.pity_4star < 0:
            raise ValueError("pity counters cannot be negative")
        if not 0 <= self.consecutive_5050_losses <= 3:
            raise ValueError("consecutive_5050_losses is capped at 3 by Capturing Radiance")
        if not 0 <= self.fate_points <= 1:
            raise ValueError("fate_points is capped at 1 since version 5.0")


@dataclass(frozen=True)
class ForecastResult:
    """Output of a PityEngine query.

    `probability` answers "at least `target_count` copies within `pull_budget`
    pulls". `distribution` is the full marginal over copy counts 0..target_count
    so a caller can render a histogram without a second solve.
    """

    probability: float
    pull_budget: int
    target_count: int
    banner: BannerKind
    distribution: tuple[float, ...] = ()
    expected_pulls: float | None = None


# ---------------------------------------------------------------------------
# Economy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LedgerEntry:
    """One immutable, append-only economic event.

    Event-sourced by design: balances are always DERIVED by folding entries, and
    are never stored as an authoritative number. This is the live-state-first
    rule applied to the wallet - a cached balance that disagrees with the fold
    is a bug in the cache, not a second source of truth.

    `delta` is signed. Income is positive, spend is negative.
    """

    entry_id: str
    occurred_at: datetime
    currency: CurrencyKind
    delta: int
    reason: str
    source: str = "manual"

    def __post_init__(self) -> None:
        if self.delta == 0:
            raise ValueError("a zero-delta ledger entry carries no information")


@dataclass
class CurrencyLedger:
    """Append-only event log over every tracked currency.

    Deliberately NOT a balance map. `balance_of` folds the log on demand. The
    entries list is the only state.
    """

    entries: list[LedgerEntry] = field(default_factory=list)

    def balance_of(self, currency: CurrencyKind) -> int:
        return sum(e.delta for e in self.entries if e.currency is currency)

    def balances(self) -> dict[CurrencyKind, int]:
        out: dict[CurrencyKind, int] = {c: 0 for c in CurrencyKind}
        for entry in self.entries:
            out[entry.currency] += entry.delta
        return out


@dataclass(frozen=True)
class IncomeVelocity:
    """Modelled income per day, used for roll-forward forecasting.

    Kept separate from the ledger because it is an ESTIMATE derived from recent
    history plus known recurring sources, not an observed event.
    """

    primogems_per_day: float = 0.0
    intertwined_fates_per_day: float = 0.0
    resin_per_day: int = 180
    sampled_over_days: int = 0


# ---------------------------------------------------------------------------
# Roster, mapped from an external profile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MappedArtifact:
    """One artifact parsed from an `equipList` entry of type ITEM_RELIQUARY."""

    item_id: int
    set_name_hash: str
    rank_level: int
    level: int
    main_stat_id: str
    main_stat_value: float
    substats: tuple[tuple[str, float], ...] = ()
    equip_type: str = ""


@dataclass(frozen=True)
class MappedWeapon:
    """One weapon parsed from an `equipList` entry of type ITEM_WEAPON.

    `refinement` is derived from `equipList[].weapon.affixMap`, whose documented
    value range is 0..4. Refinement rank presented to a user is that value plus
    one, so this field stores the PRESENTED rank 1..5 and the mapper does the
    conversion once, at the boundary.
    """

    item_id: int
    name_hash: str
    level: int
    ascension: int
    refinement: int
    rank_level: int = 0


@dataclass(frozen=True)
class MappedCharacter:
    """One roster entry parsed from `avatarInfoList`.

    Two upstream traps are absorbed here so no consumer has to know about them:

    - `talentIdList` is ABSENT from the payload at C0, not empty. The mapper
      reads it defensively, so `constellations` is 0 rather than a KeyError.
    - `skillLevelMap` does NOT include constellation-granted +3 talent levels.
      Those live in `proudSkillExtraLevelMap`. `talent_levels` here is the
      EFFECTIVE level with those bonuses already folded in, and
      `talent_levels_base` keeps the unmodified values for display.
    """

    avatar_id: int
    level: int
    ascension: int
    constellations: int
    talent_levels: dict[int, int] = field(default_factory=dict)
    talent_levels_base: dict[int, int] = field(default_factory=dict)
    friendship: int = 0
    weapon: MappedWeapon | None = None
    artifacts: tuple[MappedArtifact, ...] = ()
    element: Element | None = None
    display_name: str = ""


@dataclass(frozen=True)
class EnkaMappedProfile:
    """Normalized result of one upstream profile fetch.

    `ttl_seconds` is carried through verbatim from the upstream response. It is
    not advisory: cached data is served until it expires and STILL burns the
    rate limit, so the client suppresses requests until then.

    `characters` is empty when the showcase is closed. The upstream omits
    `avatarInfoList` entirely in that case rather than sending an empty list,
    which is why this field defaults instead of being required.
    """

    uid: str
    nickname: str = ""
    signature: str = ""
    world_level: int = 0
    adventure_rank: int = 0
    achievements: int = 0
    abyss_floor: int = 0
    abyss_chamber: int = 0
    characters: tuple[MappedCharacter, ...] = ()
    ttl_seconds: int = 60
    fetched_at: datetime | None = None
    showcase_open: bool = True


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MaterialCost:
    """A quantity of one material required by an objective."""

    material_id: int
    quantity: int
    display_name: str = ""


@dataclass(frozen=True)
class ObjectiveNode:
    """One node in the goal DAG.

    `depends_on` holds node ids, never node objects, so the graph stays
    serializable and a cycle check is a pure id-space operation.

    `resin_cost` is the total resin the node consumes if every material is
    farmed rather than drawn from inventory. `available_weekdays` is the domain
    rotation gate: an empty tuple means the node is farmable any day.
    """

    node_id: str
    kind: ObjectiveKind
    subject_id: int
    target_value: int
    depends_on: tuple[str, ...] = ()
    materials: tuple[MaterialCost, ...] = ()
    mora_cost: int = 0
    resin_cost: int = 0
    available_weekdays: tuple[int, ...] = ()
    weekly_capped: bool = False
    display_name: str = ""


@dataclass(frozen=True)
class ScheduledTask:
    """One discrete unit of work emitted by the scheduler."""

    task_id: str
    node_id: str
    cadence: TaskCadence
    resin_cost: int
    earliest_day: int
    description: str = ""


@dataclass(frozen=True)
class ResolutionPath:
    """A solved critical path through the objective DAG.

    `ordered_nodes` is a topological order that respects every dependency.
    `estimated_days` accounts for resin generation, domain weekday rotation and
    weekly boss lockouts, so it is generally LARGER than
    `total_resin / resin_per_day`.
    """

    goal_id: str
    ordered_nodes: tuple[str, ...] = ()
    tasks: tuple[ScheduledTask, ...] = ()
    total_resin: int = 0
    total_mora: int = 0
    estimated_days: int = 0
    blocked_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class Recommendation:
    """One ranked suggestion from the recommendation engine."""

    subject_id: int
    kind: ObjectiveKind
    score: float
    rationale: str
    estimated_days: int = 0
    display_name: str = ""


# ---------------------------------------------------------------------------
# Account aggregate
# ---------------------------------------------------------------------------


@dataclass
class AccountState:
    """The single in-memory aggregate the headless lane reconciles.

    Deliberately mutable, unlike most types here: it is the reconciliation
    target. Everything hanging off it is frozen, so a mutation is always an
    explicit rebind of a field rather than an in-place edit of shared state.

    `pity` is keyed by banner family because the counters are independent.
    """

    uid: str
    adventure_rank: int = 0
    world_level: int = 0
    roster: tuple[MappedCharacter, ...] = ()
    ledger: CurrencyLedger = field(default_factory=CurrencyLedger)
    pity: dict[BannerKind, PityState] = field(default_factory=dict)
    velocity: IncomeVelocity = field(default_factory=IncomeVelocity)
    goals: tuple[ObjectiveNode, ...] = ()
    last_synced_at: datetime | None = None
    last_reset_date: date | None = None

    def pity_for(self, banner: BannerKind) -> PityState:
        """Return the state for one banner, defaulting to a fresh counter.

        Never raises. A banner the account has not pulled on is genuinely at
        zero pity, so a default is the correct answer rather than an error.
        """
        return self.pity.get(banner, PityState(banner=banner))
