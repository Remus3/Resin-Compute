"""Absorbing Markov chain over the joint gacha state `(k, c, g, r)`.

SPEC 3.8. The forecast question is NOT a binomial on 1.6%. The published
1.600% is `1 / E[wishes per 5-star]`, a long-run average across a full pity
cycle, and it is never a per-wish Bernoulli parameter. Treating it as one
understates a high-pity account badly and overstates a fresh one.

State, exactly as the spec defines it:

- `k` copies of the wanted thing obtained, 0..N, ABSORBING at N
- `c` pity counter, 0..hard_pity - 1
- `g` guarantee flag, 0 or 1 - on the weapon banner this bit is the Fate Point
- `r` consecutive 50/50 losses, 0..3, Character Event banner only

Forward recurrence per pull, with `h(c)` the hazard of the pull taken while
sitting at pity `c` and `w(g, r)` the probability that a 5-star is the wanted
thing:

    no 5-star, prob (1 - h) : f[k,     c+1, g, r]              += f * (1 - h)
    5-star win, prob h * w  : f[k+1,   0,   0, r_win]          += f * h * w
    5-star loss, prob h*(1-w): f[k,    0,   1, min(r+1, 3)]    += f * h * (1 - w)

`c` saturates and never reaches hard pity, because the hazard hits 1.0 there
first and the pull is taken from `c = hard_pity - 1`. The state space is
`O(N * hard_pity * 2 * 4)`, which is 1440 floats for a single-copy character
forecast.

The win branch - SPEC 3.8.1
---------------------------
SPEC 3.8's win branch reads `f[min(k+1,N), 0, 0, 0]`, resetting `r` to 0 on
EVERY win. Taken literally that makes the Capturing Radiance cap unreachable: a
loss sets `g = 1`, the next 5-star is therefore a guaranteed win, and the
guaranteed win resets `r`, so `r` alternates 0, 1, 0, 1 and the forced win at
three losses is dead code. The engine would then run at an effective 50/50 rate
of 0.52106 rather than the 55.000% SPEC 3.2 requires of the same model.

A guaranteed 5-star is not a contested 50/50 roll, so it cannot end a run of
50/50 losses - the official wording counts occasions on which the promotional
character was the SECOND 5-star, which is three lose-then-win-on-guarantee
cycles. `r_win` is therefore `r` when the win came from the guarantee and 0 when
it came from a contested roll. `carry_radiance_through_guarantee` selects the
policy and defaults to True (correct); False reproduces the literal reading,
which is the common community simplification.

MEASURED, and the reason that simplification survives in the wild: on this
banner every loss is immediately redeemed by a guaranteed win, so `r` climbs at
most one step per copy obtained. From a fresh state the cap cannot fire before
absorption and the two policies agree to within float noise. At a banked streak
of 2, target 2 over a 200 pull budget, they diverge by +9.2385e-02 probability
and -1.4290e+01 expected pulls.

Pure and deterministic: no I/O, no globals, no clock, no randomness. The same
arguments always produce the same floats.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.types import BannerKind, PityState

from .banners import BannerConfig

# Absorption is exact under a bounded pity curve, so this only guards float
# residue - not a convergence tolerance for an open-ended sum.
_ABSORB_EPS = 1e-15

# Each state block is (g in 0..1) x (r in 0..3) = 8 slots wide.
_BLOCK = 8


@dataclass(frozen=True)
class ChainSolution:
    """Raw output of one forward solve.

    `distribution` is the marginal over copy counts 0..N at exactly
    `pull_budget` pulls. Index N means "N or more", because the chain absorbs
    there, and it is numerically identical to `probability`.

    `absorbed_by_pull[t]` is the cumulative probability of having reached N
    copies within t pulls, for t = 0 up to the horizon the solve needed. It is
    the whole answer curve, so a caller wanting many budgets should read this
    rather than re-solving per budget.
    """

    distribution: tuple[float, ...]
    probability: float
    expected_pulls: float
    absorbed_by_pull: tuple[float, ...]


def _validate(config: BannerConfig, state: PityState, target_count: int, pull_budget: int) -> None:
    if target_count < 1:
        raise ValueError("target_count must be at least 1 - asking for zero copies has no answer")
    if pull_budget < 0:
        raise ValueError("pull_budget cannot be negative")
    hard = config.hard_pity
    if state.pity_5star >= hard:
        raise ValueError(
            f"pity_5star {state.pity_5star} is at or past hard pity {hard} for {config.kind.value} - "
            "that state is unreachable because the payout would already have happened"
        )


def _initial_guarantee_bit(config: BannerConfig, state: PityState) -> int:
    """Fold PityState's two guarantee-shaped fields into the chain's single bit.

    SPEC 3.8 carries ONE bit. On the weapon banner that bit is the Fate Point
    (SPEC 3.4, capped at 1 since version 5.0); everywhere else it is the
    ordinary guarantee flag. They are deliberately not OR-ed together: the
    weapon banner's separate featured-vs-off-banner guarantee is already folded
    into the flat 0.375 branch by the spec's model, so honouring
    `has_guarantee` there as well would double-count it.
    """
    if config.kind is BannerKind.WEAPON_EVENT:
        return 1 if state.fate_points >= 1 else 0
    return 1 if state.has_guarantee else 0


def _marginal(f: list[float], target_count: int, hard: int) -> tuple[float, ...]:
    width = hard * _BLOCK
    return tuple(sum(f[k * width:(k + 1) * width]) for k in range(target_count + 1))


def solve(
    config: BannerConfig,
    state: PityState,
    target_count: int,
    pull_budget: int,
    carry_radiance_through_guarantee: bool = True,
) -> ChainSolution:
    """Run the forward recurrence and report the whole answer curve.

    The solve always runs to full absorption, which is a bounded horizon rather
    than a truncation: from any state a 5-star arrives within `hard_pity` pulls,
    and any 5-star either pays out a copy or sets the guarantee bit that makes
    the NEXT one pay out. Two 5-stars per copy is therefore the worst case, so
    `2 * hard_pity * target_count` pulls absorb the entire mass exactly. That is
    why `expected_pulls` is a finite closed number and not an estimate.
    """
    _validate(config, state, target_count, pull_budget)

    hard = config.hard_pity
    table = config.five_star
    n = target_count
    width = hard * _BLOCK
    size = (n + 1) * width

    # w depends only on (g, r), so evaluate the branch rule 8 times up front
    # instead of once per state per pull.
    w_by_slot = tuple(config.rate_up(bool(j >> 2), j & 3) for j in range(_BLOCK))

    f = [0.0] * size
    r0 = min(state.consecutive_5050_losses, 3) if config.capturing_radiance else 0
    g0 = _initial_guarantee_bit(config, state)
    f[state.pity_5star * _BLOCK + g0 * 4 + r0] = 1.0

    absorbed_offset = n * width
    absorbed_by_pull = [sum(f[absorbed_offset:])]
    distribution = _marginal(f, n, hard) if pull_budget == 0 else None

    max_steps = max(pull_budget, 2 * hard * n)
    pulls = 0
    while pulls < max_steps:
        if absorbed_by_pull[-1] >= 1.0 - _ABSORB_EPS:
            break
        nf = [0.0] * size
        for k in range(n):
            k_base = k * width
            win_base = min(k + 1, n) * width
            loss_base = k_base + 4
            for c in range(hard):
                h = table[c + 1]
                miss = 1.0 - h
                c_base = k_base + c * _BLOCK
                next_c_base = c_base + _BLOCK
                for j in range(_BLOCK):
                    mass = f[c_base + j]
                    if mass == 0.0:
                        continue
                    if miss > 0.0:
                        nf[next_c_base + j] += mass * miss
                    if h == 0.0:
                        continue
                    r = j & 3
                    w = w_by_slot[j]
                    if w > 0.0:
                        # A guaranteed 5-star is not a contested roll, so it
                        # cannot end a run of 50/50 losses. See the module note.
                        win_r = r if (carry_radiance_through_guarantee and j >= 4) else 0
                        nf[win_base + win_r] += mass * h * w
                    if w < 1.0:
                        nf[loss_base + (r + 1 if r < 3 else 3)] += mass * h * (1.0 - w)
        for i in range(absorbed_offset, size):
            nf[i] += f[i]
        f = nf
        pulls += 1
        absorbed_by_pull.append(sum(f[absorbed_offset:]))
        if pulls == pull_budget:
            distribution = _marginal(f, n, hard)

    if distribution is None:
        # Either the budget outran full absorption or it outran the horizon; in
        # both cases the marginal has stopped moving, so the final grid is it.
        distribution = _marginal(f, n, hard)

    # E[T] = sum over t >= 0 of P(T > t). Every term past full absorption is
    # zero, so the finite series is the exact expectation.
    expected_pulls = sum(1.0 - a for a in absorbed_by_pull)

    return ChainSolution(
        distribution=distribution,
        probability=distribution[n],
        expected_pulls=expected_pulls,
        absorbed_by_pull=tuple(absorbed_by_pull),
    )


def pull_distribution(
    config: BannerConfig,
    state: PityState,
    max_pulls: int | None = None,
    carry_radiance_through_guarantee: bool = True,
) -> tuple[float, ...]:
    """Probability that the FIRST wanted copy lands on exactly pull `t`.

    Index 0 is always 0.0 - a copy cannot arrive before a pull is spent. The
    returned tuple runs to full absorption and sums to 1.0, so it is a genuine
    probability mass function rather than a truncated head. `max_pulls` clips
    it, in which case the tail probability is simply absent and the sum is the
    cumulative chance by then.
    """
    solution = solve(config, state, 1, 0, carry_radiance_through_guarantee)
    cumulative = solution.absorbed_by_pull
    mass = [0.0]
    # Clamped at zero: the cumulative curve is monotone by construction, so a
    # negative difference would only ever be float residue, never real mass.
    mass.extend(max(0.0, cumulative[t] - cumulative[t - 1]) for t in range(1, len(cumulative)))
    if max_pulls is None:
        return tuple(mass)
    if max_pulls < 0:
        raise ValueError("max_pulls cannot be negative")
    trimmed = mass[: max_pulls + 1]
    trimmed.extend([0.0] * (max_pulls + 1 - len(trimmed)))
    return tuple(trimmed)


def expected_wishes_per_five_star(table: tuple[float, ...]) -> float:
    """E[wishes between 5-stars] for one hazard table.

    Straight expectation over the geometric-with-ramp payout distribution:
    `sum over n of n * h(n) * prod over i < n of (1 - h(i))`. Terminates exactly
    because the table ends at a hazard of 1.0.
    """
    if len(table) < 2:
        raise ValueError("hazard table is empty")
    expected = 0.0
    survival = 1.0
    for n in range(1, len(table)):
        expected += n * survival * table[n]
        survival *= 1.0 - table[n]
    if expected <= 0.0:
        raise ValueError("hazard table yields a non-positive expectation")
    return expected


def consolidated_rate(table: tuple[float, ...]) -> float:
    """`1 / E[wishes per 5-star]` - the published "consolidated probability".

    This is the SELF-CHECK hook for a hazard table. The character table returns
    0.0160521 against HoYoverse's published 1.600%, and that 0.005pp agreement
    is the evidence the curve is right. A table that has been mis-transcribed
    moves this number far more than it moves any single hazard value, which is
    what makes it a better guard than spot-checking entries.
    """
    return 1.0 / expected_wishes_per_five_star(table)
