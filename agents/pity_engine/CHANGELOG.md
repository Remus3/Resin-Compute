# PityEngine - changelog

The engine revision is `ENGINE_VERSION` in `__init__.py`; that constant is the
single source of truth and this file is the full per-version history. New
ENGINE bumps PREPEND one entry to the changelog section below (newest-first);
never extend a prior version's line.

Convention lifted from Riot Commander's Daemon Slayer, along with the shape of
the engine itself: a pure, deterministic, versioned local compute core exposed
over a loopback HTTP port, with new capability added as opt-in arguments that
are byte-identical to the prior version at their defaults.

---

## Service changes at engine revision 0.1.0

`ENGINE_VERSION` is the COMPUTE revision. It is returned to every caller as
`engine_version` and a consumer reads it to decide whether a cached forecast is
still valid. The entries in this section changed the SERVICE around the compute
and left every forecast byte-identical, so the revision deliberately did NOT
move - bumping it would have signalled a compute change that did not happen and
invalidated correct caches. A change that alters a number this engine returns
bumps the revision and gets its own section above this one.

### The port is now bound EXCLUSIVELY, and a second bind fails loudly

`ThreadingHTTPServer` inherits `allow_reuse_address = True`, which sets
`SO_REUSEADDR`. On POSIX that only relaxes TIME_WAIT, but on Windows
`SO_REUSEADDR` permits two live sockets to bind the same address, and the second
bind SUCCEEDS while the first process keeps serving. A second engine started by
accident therefore came up silently, answered nothing, and left the operator
reading a health file that said `alive`.

`_ExclusiveHTTPServer` drops `SO_REUSEADDR` and sets `SO_EXCLUSIVEADDRUSE` on
Windows instead - the flag that means on Windows what `SO_REUSEADDR` means on
POSIX. The observable change for a caller:

- `build_server()` now RAISES `OSError` rather than quietly binding a port
  another process holds.
- `main()` exits **2** when the port it needs is already held. 0 remains a clean
  shutdown.
- The listening socket is still closed on shutdown, so TIME_WAIT does not apply
  to it and an immediate restart works. The engine runs in the FOREGROUND and
  ctrl-C then restart is its ordinary edit loop, so that is pinned by
  `agents/pity_engine/tests/test_service.py` - turning off address reuse is
  exactly the change that could have broken it.

The full nine-cell matrix of first-socket and second-socket flag combinations is
reproduced in `agents/pity_engine/tests/test_service.py`. Exactly one cell
double-binds - `SO_REUSEADDR` on BOTH sockets - and the `first=none` and
`first=exclusive` rows are kept as the controls that prove the matrix is not
simply refusing everything.

**Which half is load-bearing was MEASURED, and it is not the one the name
suggests.** `first=none` and `first=exclusive` are identical columns, so with
`allow_reuse_address = False` already set, adding `SO_EXCLUSIVEADDRUSE` changes
no observable outcome against a listening socket on win32. Dropping
`SO_REUSEADDR` is the half that closes the defect; two stock servers are the
`reuse`/`reuse` cell. The `setsockopt` is kept because it is correct, because it
is the documented Windows spelling of the intent, and because it would matter if
a future caller re-enabled reuse - not because it is what fixed this.

This landed at one call site first, in `surface/server.py`, and reached
`agents/pity_engine/__main__.py` later because the engine had kept the stock
server. The two are now the same shape; the engine's version is derived from
that sibling fix rather than independently invented.

---

## 0.1.0 - initial engine

Shipped:

- `banners.py` - five-star hazard tables that COMPUTE their own hard pity by
  ramping until the value clips at 1.0, so an inconsistent (ramp, hard pity)
  pair is not expressible. Character/standard/chronicled curve (0.006 base,
  ramp from 74 at 0.06, hard pity 90) and the weapon curve (0.007 base, ramp
  from 63 at a tunable increment). Four-star curves for the character/standard
  and weapon banners, both with their real soft-pity step. Rate-up branch rules
  for all four families, and `BannerConfig` binding a curve pair to a branch
  rule and a Capturing Radiance flag.
- `markov.py` - the absorbing Markov chain over `(k, c, g, r)` from
  SPEC 3.8, plus `pull_distribution` over pulls-to-first-rate-up and
  `consolidated_rate`, the table self-check that computes `1 / E[wishes per
  5-star]`.
- `forecast.py` - `probability_of_success` returning a populated
  `ForecastResult`, and `pulls_needed_for_confidence`, its inverse, answering
  "how many more do I need".
- `__main__.py` - stdlib `http.server` service on 127.0.0.1:8790 mirroring
  Daemon Slayer's 8860. `GET /health`, `POST /forecast`, `--host`, `--port`.
  Fail-soft at the request boundary: a malformed request returns 400 with a
  friendly JSON message while the raw exception goes to the log, never into the
  response body.
- 76 tests across four files (curves 22, markov 15, forecast 16, service 23),
  including a named regression guard per correction below.

### Three corrections to the original brief, all guarded by tests

1. **Capturing Radiance replaces the flat 50/50.** The brief specifies a flat
   50% rate-up chance. That has been obsolete since version 5.0. HoYoverse
   publishes a consolidated 55.000% and a hard cap that makes four consecutive
   50/50 losses impossible. The engine implements a solved per-roll
   `CAPTURING_RADIANCE_P = 0.52106` plus a forced win at three losses, which is
   the pair that reproduces the published 55.000% over 50/50 rolls. The naive
   substitutions are all wrong and all asserted: flat 0.50 uncapped gives
   50.00% (the pre-5.0 behaviour the brief described), flat 0.55 with the cap
   overshoots to 57.35%, and (.5, .5, .5, 1.0) undershoots to 53.33%.
   Capturing Radiance is scoped to the Character Event banner only.
   Guard: `test_capturing_radiance_solves_to_the_published_55_percent` and
   siblings in `tests/test_pity_curves.py`.

2. **The weapon curve saturates at pity 77, not 79 or 80.** The brief specifies
   a 7% ramp from pull 63 "up to pull 79" with hard pity at 80. That curve is
   arithmetically impossible: `0.007 + 0.07 * (76 - 62)` is 0.987 and the next
   step is 1.057, so the ramp clips at pull 77 and pity 78..80 is unreachable.
   Hard pity is therefore derived from the curve rather than declared beside
   it, and the increment is exposed as a tunable parameter because the exact
   micro-curve is not pinned by public data - 7.0, 6.6, 6.0 and 5.8 percent all
   overshoot the published 1.850% consolidated rate by more than the character
   banner's error margin. Incidentally, a hard pity of 79 is consistent with a
   6% ramp and never with the 7% the brief also states.
   Guard: `test_weapon_curve_saturates_at_pity_77`.

3. **The forecaster signature needs a pull budget.** The brief's
   `calculateProbabilityOfSuccess(stats, targetCount)` is unanswerable. Success
   probability is always success WITHIN SOME NUMBER OF PULLS, and none of
   `{currentPity, hasGuarantee, fatesAvailable}` plus `targetCount` bounds the
   pulls; given unlimited pulls the answer is 1.0 for every reachable state.
   `fatesAvailable` does not rescue it either - it is a wallet quantity saying
   what the caller can afford today, not what they intend to spend. The
   implemented signature takes `pull_budget` explicitly. The related trap is
   also avoided: the published 1.600% is `1 / E[wishes per 5-star]` with
   E = 62.297, a long-run average over a full pity cycle, and it is never a
   per-wish Bernoulli parameter, so the model is an absorbing Markov chain and
   not a binomial.
   Guards: `test_validation_rejects_a_question_with_no_answer` and
   `test_forecast_is_not_a_binomial_on_the_consolidated_rate`.

### A fourth correction, raised during implementation and adopted as SPEC 3.8.1

SPEC 3.8's original win branch read `f[min(k+1,N), 0, 0, 0]`, resetting the
consecutive-50/50-loss counter on EVERY win. Taken literally that makes
Capturing Radiance unreachable: a loss sets the guarantee bit, the next 5-star
is therefore a guaranteed win, and a guaranteed win resets the counter, so the
counter alternates 0, 1, 0, 1 and the forced win at three losses is dead code.
The engine would then run at an effective 50/50 rate of 0.52106 rather than the
55.000% the same spec section requires.

A guaranteed 5-star is not a contested 50/50 roll, so it cannot end a run of
50/50 losses - the official wording counts occasions on which the promotional
character was the SECOND 5-star, which is three lose-then-win-on-guarantee
cycles. The win branch therefore preserves the counter when the win came from
the guarantee and clears it when the win came from a contested roll.
`carry_radiance_through_guarantee` selects the policy and defaults to True
(correct); passing False reproduces the literal reading, retained because it is
the common community simplification. The spec adopted this as section 3.8.1.

MEASURED divergence, character banner, target 2 over a 200 pull budget:

| start `consecutive_5050_losses` | delta probability | delta expected_pulls |
|---|---|---|
| 0 | +1.11e-16 | +5.68e-14 |
| 1 | +1.11e-16 | +5.68e-14 |
| 2 | +9.2385e-02 | -1.4290e+01 |

On this banner every loss is immediately redeemed by a guaranteed win, so the
streak climbs at most one step per copy obtained and the cap cannot fire before
absorption from a fresh state. That is why the two policies are identical to
float noise at start state 0 and diverge by nine percentage points at start
state 2, and it is why `test_radiance_carry_beats_the_spec_literal_recurrence`
starts at a banked streak of 2. Asserting a strict inequality from a default
start state compares two numbers equal to within float noise, and the noise
empirically points the wrong way.

### Modelling notes

- The chain carries ONE guarantee bit, per SPEC 3.8. On the weapon banner that
  bit is the Fate Point (SPEC 3.4, capped at 1 since version 5.0); on the other
  families it is the ordinary guarantee flag. They are not OR-ed together,
  because the weapon banner's separate featured-vs-off-banner guarantee is
  already folded into the flat 0.375 branch and honouring `has_guarantee` there
  as well would double-count it.
- SPEC 3.7 pins the Chronicled five-star curve but SPEC 3.5 names only
  "character / standard" and "weapon banner" for the four-star step, so
  Chronicled inherits the character/standard four-star table rather than
  getting an invented one.
- `expected_pulls` is a closed number, not a truncated estimate: from any state
  a 5-star arrives within one pity cycle, and any 5-star either pays out or
  sets the guarantee bit that makes the next one pay out, so two pity cycles
  per copy absorb the entire probability mass exactly.
- Four-star pity is modelled in the tables but is not yet folded into the
  forecast chain. The five-star and four-star counters are only partially
  independent (SPEC 3.6: a five-star resets the four-star counter, but not the
  reverse), so wiring it in is a joint-state change rather than a second
  independent chain, and it waits for a version that needs it.
