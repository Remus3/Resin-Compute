# ADR-003: Markov chain forecaster, and three corrections to the brief

**Status:** Accepted, 2026-09-06

## Context

The originating brief specified the gacha mathematics in detail. A verification
pass against community-measured sources and published HoYoverse rates on
2026-09-06 confirmed most of it and found three defects, one of which is
arithmetically impossible as written.

**Confirmed exactly as briefed:**

- Character banner base 0.006 for pity 1 through 73.
- Soft pity from 74, ramping `0.006 + 0.06 * (n - 73)`.
- P(89) = 0.966 exactly, matching the brief's "roughly 96.6%".
- Hard pity 1.0 at 90, which is a clip - the unclipped formula gives 1.026.
- Weapon banner base 0.007 for 1 through 62, soft pity from 63.
- Weapon 75/25 with per-featured-weapon probability 0.375.
- Fate Points capped at 1, changed in version 5.0 from 2.

The character table's own self-check corroborates it: folding it gives a
consolidated rate of 1.6052% against HoYoverse's published 1.600%, an agreement of
0.005 percentage points.

## Decision

### Correction 1: the 50/50 is not 50/50

The brief specifies a flat 50% rate-up chance on a non-guaranteed 5-star. That has
been obsolete since **version 5.0**, which added **Capturing Radiance**. HoYoverse
publishes a base trigger probability of 0.018% and a **consolidated 55.000%**
probability that a non-guaranteed 5-star is the promotional character, plus a hard
cap making four consecutive 50/50 losses impossible.

Implemented model:

```
p_rate_up_on_5050 = 0.52106
forced win when consecutive_5050_losses == 3
```

`0.52106` is solved so the long-run rate reproduces the official 55.000%. Naive
alternatives were computed and rejected:

| Model | Long-run rate-up win rate |
|---|---|
| flat 0.50, no cap (pre-5.0) | 50.00% |
| flat 0.55 with the cap | 57.35%, overshoots |
| (0.5, 0.5, 0.5, 1.0) ramp | 53.33%, undershoots |
| **flat 0.52106 with the cap** | **55.000%, matches** |

Capturing Radiance applies only to Character Event Wish and Character Event
Wish-2. It does not apply to the weapon, standard or Chronicled banners.

### Correction 2: the weapon curve cannot reach pull 79

The brief says the weapon soft pity increases "7% per pull up to pull 79" with
hard pity at 80. Computed with `P_n = 0.007 + 0.07 * (n - 62)`:

```
P(76) = 0.987
P(77) = 1.057    exceeds 1.0
```

A 7% ramp from pull 63 **saturates at pull 77**, three pulls before the stated
hard pity. The briefed curve cannot exist. This is also the source of the
77-versus-80 disagreement across public implementations: some encode hard pity 77
because they derived it from the ramp, others encode 80 from the published
guarantee text and are internally inconsistent.

The engine clips to 1.0 and computes effective hard pity from the table rather
than hardcoding it. The increment is a **tunable parameter**, because the exact
micro-curve is not pinned by public data: increments of 7.0%, 6.6%, 6.0% and 5.8%
all overshoot the published 1.850% consolidated rate by more than the character
banner's error margin. For the ramp to genuinely first reach 1.0 at pull 80 the
increment would have to be at most 5.84%.

The published guarantee of "at least once per 80 attempts" is satisfied trivially
by any of these. What the engine must not do is claim a 5-star can occur at pity
78 through 80 under the 0.07 model, because it cannot.

### Correction 3: a probability of success needs a pull budget

The brief's signature is unanswerable:

```typescript
function calculateProbabilityOfSuccess(stats: PityStats, targetCount: number): number;
```

`PityStats {currentPity, hasGuarantee, fatesAvailable}` plus a target count
carries no horizon, so "probability of success" has no defined value. The
implemented signature adds one:

```python
def probability_of_success(state, target_count, pull_budget, banner) -> ForecastResult
```

`fatesAvailable` was also moved off the pity state and onto the ledger, where it
belongs - it is a wallet quantity, not a pity quantity. The weapon banner's Fate
Points, which are a genuinely different thing, stay on `PityState` as
`fate_points`.

### The model itself

An absorbing Markov chain over `(k, c, g, r)`: copies obtained, pity counter,
guarantee or Fate Point flag, and consecutive 50/50 losses. Per-pull transitions
are given in `docs/SPEC_SCAFFOLD.md` section 3.8. State space is
`O(N * 90 * 2 * 4)`.

Explicitly **not** a binomial on 1.6%. The 1.600% figure is `1 / E[wishes per
5-star]`, with E computed at 62.297 wishes. It is a long-run average across a
full pity cycle and is never a per-wish Bernoulli parameter at any point on the
curve.

## Consequences

- The engine is correct for the current game version rather than for the pre-5.0
  one, which is what a player would actually be planning against.
- Each of the three corrections carries a named regression test, so a future
  contributor who "fixes" the weapon curve back to pull 79 fails CI.
- The tunable weapon increment is honest about a genuine gap in public data
  instead of hiding it behind a hardcoded constant.
