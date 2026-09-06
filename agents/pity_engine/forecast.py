"""Public forecasting API.

This is the only module a caller outside the engine should need. It owns input
validation, banner selection and the translation of a raw chain solve into the
`ForecastResult` contract in `core/types.py`.
"""
from __future__ import annotations

from core.types import BannerKind, ForecastResult, PityState

from .banners import BannerConfig, banner_config
from .markov import solve

# Confidence comparisons run against a solved float, so an exact `>=` against
# 1.0 would fail on ordinary summation residue. This is a float tolerance, not
# a modelling fudge.
_CONFIDENCE_EPS = 1e-12


def _config_for(banner: BannerKind, weapon_increment: float | None) -> BannerConfig:
    if weapon_increment is None:
        return banner_config(banner)
    return banner_config(banner, weapon_increment=weapon_increment)


def probability_of_success(
    state: PityState,
    target_count: int,
    pull_budget: int,
    banner: BannerKind = BannerKind.CHARACTER_EVENT,
    weapon_increment: float | None = None,
    carry_radiance_through_guarantee: bool = True,
) -> ForecastResult:
    """Probability of landing at least `target_count` copies within `pull_budget` pulls.

    Why the budget parameter exists
    -------------------------------
    The original brief specifies `calculateProbabilityOfSuccess(stats,
    targetCount)`, where `stats` is `{currentPity, hasGuarantee,
    fatesAvailable}`. That signature is UNANSWERABLE. "Probability of success"
    is a probability of success WITHIN SOME NUMBER OF PULLS, and none of those
    four inputs bounds the number of pulls. Given unlimited pulls the answer is
    1.0 for every reachable state and every target, so the brief's function is
    either the constant 1.0 or it is under-specified. `fatesAvailable` looks
    like it might supply the bound, but it is a WALLET quantity - it says what
    the caller can afford today, not what they intend to spend, and a forecast
    that silently equates the two cannot answer "what if I save for two more
    patches". SPEC 3.8 resolves this by making the budget an explicit argument.

    The second correction is the model itself: this is NOT a binomial on 1.6%.
    See `markov` for why, and for the absorbing chain that replaces it.

    Returns a fully populated `ForecastResult`, including the marginal over copy
    counts 0..target_count and the expected number of pulls to reach the target
    ignoring the budget. SPEC 3.8 annotates this function `-> float`; the richer
    return is the `ForecastResult` dataclass that `core/types.py` defines for
    exactly this call, and `result.probability` is the float the spec names.

    Raises `ValueError` on a request that has no answer.
    """
    if not isinstance(target_count, int) or isinstance(target_count, bool):
        raise ValueError("target_count must be an integer number of copies")
    if not isinstance(pull_budget, int) or isinstance(pull_budget, bool):
        raise ValueError("pull_budget must be an integer number of pulls")
    if target_count < 1:
        raise ValueError("target_count must be at least 1 - a forecast for zero copies has no meaning")
    if pull_budget < 0:
        raise ValueError("pull_budget cannot be negative - a forecast needs a real number of pulls")

    config = _config_for(banner, weapon_increment)
    solution = solve(
        config,
        state,
        target_count,
        pull_budget,
        carry_radiance_through_guarantee=carry_radiance_through_guarantee,
    )
    return ForecastResult(
        probability=solution.probability,
        pull_budget=pull_budget,
        target_count=target_count,
        banner=banner,
        distribution=solution.distribution,
        expected_pulls=solution.expected_pulls,
    )


def pulls_needed_for_confidence(
    state: PityState,
    target_count: int,
    confidence: float,
    banner: BannerKind = BannerKind.CHARACTER_EVENT,
    weapon_increment: float | None = None,
    carry_radiance_through_guarantee: bool = True,
) -> int:
    """Smallest pull budget whose success probability reaches `confidence`.

    The inverse of `probability_of_success`, and the shape most callers actually
    want: "how many more do I need". Solved once and read off the cumulative
    curve rather than by re-solving per candidate budget, so it costs the same
    as a single forecast.

    `confidence` of 0.0 returns 0 - no pulls are needed to be zero percent sure.
    `confidence` of 1.0 is reachable and finite here, because hard pity bounds
    the worst case at two 5-stars per copy.
    """
    if target_count < 1:
        raise ValueError("target_count must be at least 1 - a forecast for zero copies has no meaning")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must lie between 0.0 and 1.0 inclusive")
    if confidence <= 0.0:
        return 0

    config = _config_for(banner, weapon_increment)
    solution = solve(
        config,
        state,
        target_count,
        0,
        carry_radiance_through_guarantee=carry_radiance_through_guarantee,
    )
    for pulls, cumulative in enumerate(solution.absorbed_by_pull):
        if cumulative >= confidence - _CONFIDENCE_EPS:
            return pulls
    raise ValueError(
        "confidence is not reachable within the modelled horizon for this banner - "
        "re-check the target count and pity state"
    )
