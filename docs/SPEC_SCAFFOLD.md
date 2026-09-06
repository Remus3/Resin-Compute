# ResinCompute scaffold contract

Authoritative build contract for the initial scaffold. Every build slice reads
this file first. Where this file and a prompt disagree, THIS FILE WINS.

ASCII only. No em-dashes, no en-dashes, no smart quotes. Use ` - ` for a clause
break. This is enforced by `tools/precommit_gate.py` and the git hooks.

---

## 0. Identity

- Repo / product: **ResinCompute**
- Compute sub-engine: **PityEngine** (lives in `agents/pity_engine/`)
- Two-tier naming deliberately mirrors Riot Commander (repo) / Daemon Slayer
  (engine). Do not rename either half.
- Trademark posture: no HoYoverse-coined proper noun appears in a module name,
  package name, class name or CLI verb. Game data VALUES (character names, item
  names) are fine as data; they are not identifiers.

## 1. Stack (inherited from Riot Commander, measured 2026-09-06)

Riot Commander is Python. Measured: 2869 `.py` against 1 generated `.d.ts`. It
carries NO `package.json`, `tsconfig.json`, Biome, ESLint, Prettier, Vitest,
Jest, Dockerfile or docker-compose. The original brief asked for a TypeScript
toolchain; the operator chose true RC inheritance instead, so:

| Concern | RC tool | ResinCompute tool |
|---|---|---|
| Lint | `ruff.toml` | `ruff.toml` (ported) |
| Tests | `pytest.ini` + `conftest.py` | same |
| Types | `mypy.ini` | same |
| CI | 3 GH Actions workflows w/ docs path-split | `ci.yml` + `docs-guards.yml` |
| Hooks | `.githooks/` + `core.hooksPath` | same |
| Headless lane | `ops/` supervisor + scheduled tasks | `ops/` + `headless/` |
| Compute engine | Daemon Slayer HTTP `:8860` | PityEngine HTTP `:8790` (ADR-004) |

**TypeScript interfaces named in the brief are delivered as Python dataclasses.**
Python target: **3.11** (mypy pin). Ruff `target-version = "py311"`.
RC targets py39; we do not inherit that constraint because this is a new tree
with no py39 deployment surface. This is a deliberate, recorded divergence.

No Docker in this scaffold. RC has none, so there is nothing to inherit. If
containers are wanted later that is a new decision, recorded as an ADR.

## 2. Hard rules inherited verbatim

- **Always `py_compile` before declaring done.** Syntax errors crash silently
  under `pythonw.exe`.
- **Atomic writes only:** `tmp.write_text(...); tmp.replace(target)`. Never
  write a state file in place. `core/atomic_io.py` is the only sanctioned path.
- **Never `Stop-Process`** on Windows. Use `taskkill /F /PID`.
- **No em-dashes or en-dashes, ever**, in any authored text including code,
  comments, docstrings, `.md` and commit messages.
- **Never add a `Co-Authored-By: Claude` trailer.** `.githooks/commit-msg`
  strips it, matching RC operator policy.
- **A fresh clone runs zero hooks.** `core.hooksPath` is local config and is not
  cloned. First action in any fresh clone is `python scripts/install_hooks.py`.
- **State assumptions explicitly before coding.**
- **Live-state-first.** Derive state from the current response only. No stale
  cache treated as truth, no hardcoded roster.
- **Never surface a raw API or error string in a user-facing surface.** Catch,
  render a friendly degraded state, log the raw error.

## 3. VERIFIED domain constants

Everything in this section was verified against primary sources on 2026-09-06.
Where the original brief was wrong, the brief's value is recorded next to the
correction so nobody re-introduces it.

### 3.1 Character Event Wish - CONFIRMED as briefed

```
base            = 0.006 for pity 1..73
soft pity ramp  = 0.006 + 0.06 * (n - 73) for n in 74..89
hard pity       = 1.0 at n == 90
```
- P(89) = 0.966 exactly. The brief's "roughly 96.6%" is correct.
- The unclipped formula gives 1.026 at n=90, so 90 is a CLIP, not an evaluation.
- Consolidated rate from this table computes to 1.6052% against HoYoverse's
  published 1.600%. That 0.005pp agreement is the self-check that the table is
  right. Assert it in a test.

### 3.2 The 50/50 is NOT 50/50 - brief REFUTED

The brief specifies a flat 50% rate-up chance. That has been obsolete since
**version 5.0**, which added **Capturing Radiance**.

Official HoYoverse FAQ: base trigger probability 0.018%, and there is a
"consolidated probability of **55.000%**" that a non-guaranteed 5-star is the
promotional character. Hard cap: you cannot lose four 50/50 rolls in a row.

Model to implement:
```
p_rate_up_on_5050 = 0.52106      # solved so the long-run rate hits 55.000%
forced win when consecutive_5050_losses == 3
```
Naive alternatives and why they are wrong (record these in the test file):
- flat 0.50, no cap  -> long-run 50.00%, pre-5.0 behaviour
- flat 0.55 + cap    -> long-run 57.35%, overshoots the official 55.000%
- (.5,.5,.5,1.0)     -> 53.33%, undershoots

Capturing Radiance applies ONLY to Character Event Wish and Character Event
Wish-2. It does NOT apply to weapon, standard or Chronicled banners.

### 3.3 Weapon Event Wish - brief ARITHMETICALLY IMPOSSIBLE

The brief says "increasing 7% per pull up to pull 79" with hard pity at 80.
Computed: with `P_n = 0.007 + 0.07 * (n - 62)`,
```
P(76) = 0.987
P(77) = 1.057   <- exceeds 1.0
```
A 7% ramp from pull 63 **saturates at pull 77**, three pulls before the stated
hard pity. The brief's curve cannot reach pull 79. Implement as:
```
base            = 0.007 for pity 1..62
soft pity ramp  = 0.007 + INCREMENT * (n - 62) from n = 63, clipped to 1.0
INCREMENT       = 0.07 default, TUNABLE
effective hard pity = first n where the clip binds (77 at the 0.07 default)
```
The published guarantee is "at least once per 80 attempts", which the model
satisfies trivially. Do not claim a 5-star can occur at pity 78..80 under the
0.07 model; it cannot. Exposing INCREMENT as tunable is required because the
exact micro-curve is NOT pinned by public data: 7.0/6.6/6.0/5.8 percent all
overshoot the published 1.850% consolidated rate by more than the character
banner's error margin.

### 3.4 Weapon 75/25 and Fate Points - CONFIRMED as briefed

- 75% of weapon 5-stars are one of the two featured weapons; 25% off-banner.
- Per featured weapon: **0.375**.
- **Max Fate Points = 1**, changed in version 5.0 (was 2). Worst case is now
  160 wishes, previously 240.
- Fate Points reset to 0 on obtaining the chosen weapon, on cancelling or
  switching the charted course, and when the banner ends. Pity and the guarantee
  flag DO carry across weapon banners; Fate Points do NOT. Banner-end and course
  change are exogenous events the caller injects.
- No Capturing Radiance on the weapon banner.

### 3.5 Four-star pity - brief IMPRECISE

There is a real soft-pity step, and the weapon banner differs:
```
character / standard : 0.051 for 1..8, 0.561 at 9, 1.0 at 10
weapon banner        : 0.060 for 1..7, 0.660 at 8, 1.0 at 9
```
Rate-up: 50% featured on the character banner (its own separate 50/50 and
guarantee flag), 75% on the weapon banner.

### 3.6 Pity counter independence

Partially independent, and the asymmetry matters:
- A 4-star does NOT touch the 5-star counter.
- A 5-star DOES reset the 4-star counter, because the guarantee is worded
  "4-star or above every 10 wishes".
- Counters are separate per banner TYPE. Character Event Wish and Character
  Event Wish-2 share one counter.

### 3.7 Standard and Chronicled

- Standard (Wanderlust Invocation): 5-star same 74/90 curve, 4-star base 5.100%
  hard pity 10. No 50/50, no featured, no Capturing Radiance.
- Chronicled Wish: same 74/90 5-star curve, own independent counter, **50.000%**
  designated-item chance, miss grants 1 Fate Point and guarantees the next.
  No Capturing Radiance.

### 3.8 The forecaster API contract

The brief's signature is under-specified:
```
function calculateProbabilityOfSuccess(stats, targetCount): number
```
`PityStats {currentPity, hasGuarantee, fatesAvailable}` plus `targetCount`
carries **no pull budget**, so the question "probability of success" has no
answer. A budget parameter is required. Implement:

```python
def probability_of_success(
    state: PityState,
    target_count: int,
    pull_budget: int,
    banner: BannerKind = BannerKind.CHARACTER_EVENT,
) -> ForecastResult
```

**CORRECTION.** This block originally annotated `-> float`, contradicting the
same document's own `ForecastResult` contract, which exists for exactly this
call. Slices B and F both hit it independently, and in F's case it crashed a
test with `TypeError: unsupported format string passed to
ForecastResult.__format__` - a mismatched return annotation does not stay
theoretical, it reaches a caller that formats the value.

The return is `ForecastResult`. The spec's float is `result.probability`.

Do NOT implement this as a binomial on 1.6%. 1.600% is `1 / E[wishes per
5-star]` (E = 62.297 wishes), a long-run average over a full pity cycle. It is
never a per-wish Bernoulli parameter.

The correct object is an absorbing Markov chain over the joint state
`(k, c, g, r)`:
- `k` copies obtained, 0..N, absorbing at N
- `c` pity counter
- `g` guarantee flag / Fate Point, 0 or 1
- `r` consecutive 50/50 losses, 0..3 (character banner only)

Forward recurrence, per pull, with `h(c)` the 5-star hazard and `w(g, r)` the
probability that a 5-star is the rate-up:
```
no 5-star,     prob (1 - h(c)) : f[k, c+1, g, r]                 += f * (1-h)
5-star, win,   prob h * w      : f[min(k+1,N), 0, 0, 0]           += f * h * w
5-star, loss,  prob h * (1-w)  : f[k, 0, 1, min(r+1, 3)]          += f * h * (1-w)
```
`w(g, r)` per banner:
- character: `1.0 if g else (1.0 if r == 3 else 0.52106)`
- weapon:    `1.0 if g else 0.375`
- chronicled/classic: `1.0 if g else 0.5`

Answer: `P(k >= N within P pulls) = sum over c,g,r of f_P[N, c, g, r]`.

State space stays `O(N * 90 * 2 * 4)`. Note `c` saturates and never reaches 90
(character) or 77 (weapon at the 0.07 default) because the hazard hits 1.0 first.

### 3.8.1 CORRECTION - the win branch above is an oversimplification

The win branch as written resets `r` to 0 on EVERY win, guaranteed wins included.
Taken literally that makes Capturing Radiance unreachable dead code, and slice B
caught it during implementation:

```
start r=0, g=0
lose a 50/50      -> g=1, r=1
next 5-star       -> g=1 so it is guaranteed, wins, resets to g=0, r=0
```

`r` therefore alternates 0, 1, 0, 1 and never reaches 2 or 3, so the forced win
at three consecutive losses can never fire.

The official wording is "if the promotional character was the **second** 5-star
on three consecutive occasions". That describes three consecutive
lose-then-win-on-guarantee CYCLES. A guaranteed pull is not a contested 50/50
roll, so it must NOT reset the streak.

Correct policy, and the engine default:

```
5-star, win on a CONTESTED roll (g == 0) : f[min(k+1,N), 0, 0, 0]     r resets
5-star, win on a GUARANTEED roll (g == 1): f[min(k+1,N), 0, 0, r]     r CARRIES
5-star, loss                             : f[k, 0, 1, min(r+1, 3)]
```

Both policies are implemented behind `carry_radiance_through_guarantee`, which
defaults to True. The literal reading is retained as the False branch because it
is the common community simplification.

**MEASURED divergence** at target 2 over a 200 pull budget, character banner:

| start `consecutive_5050_losses` | delta probability | delta expected_pulls |
|---|---|---|
| 0 | +1.11e-16 | +5.68e-14 |
| 1 | +1.11e-16 | +5.68e-14 |
| 2 | **+9.2385e-02** | **-1.4290e+01** |

So the policies are identical to float noise from a fresh state and diverge hard
once the streak is one short of the cap: nine percentage points of probability
and fourteen fewer expected pulls. That is the cap doing its job.

**Consequence for tests, and this is a real trap that already bit once:** a test
asserting the two policies DIFFER must start at `consecutive_5050_losses = 2`,
where the cap actually bites. Asserting a strict inequality from a default start
state compares two numbers equal to within float noise, so the result is decided
by the last bit rather than by the model - and empirically the noise points the
WRONG way, making `carried.expected_pulls < literal.expected_pulls` fail at
start state 0 even though the modelled relationship is real at start state 2.

## 4. VERIFIED data-source posture (license gate)

CLAUDE.md's third-party lift rule applies. Findings from the 2026-09-06 pass:

| Source | Real location | License | Verdict |
|---|---|---|---|
| GenshinData (Dimbreath) | `github.com/Dimbreath/GenshinData` is **404, DMCA'd 2022**. Live successor is `gitlab.com/Dimbreath/animegamedata2` | **NONE. No LICENSE file, no copyright line.** | **DO NOT VENDOR. Do not design an ingest path against it.** |
| genshin-db | `github.com/theBowja/genshin-db`, npm `genshin-db` | MIT, `Copyright (c) 2020 theBowja`, manifest agrees | **Code MIT. Bulk data NO** - its own readme says data is sourced from the Fandom wiki (CC BY-SA 3.0) and GenshinData. The MIT badge does not clear the payload. |
| Enka API docs | `github.com/EnkaNetwork/API-docs` | **NONE** | Protocol facts are usable. `store/*.json` is **fetch-only, do not vendor**. |
| Project Amber | base URL is **`https://gi.yatta.moe/api/v2`**, not `ambr.top` | **NONE**, no published ToS or rate limits | Fetch at own risk. Treat as unstable. Do not vendor. |
| `enka-py` (pypi `enka`) | maintained, 2026-06-26 | **GPL-3.0** | **DO NOT VENDOR** - it wraps HoYoverse game data. See the ADR-006 note below. |
| `enkanetwork.py` | last release 2023-08-30 | MIT, `Copyright 2022 M-307` | Vendorable but unmaintained ~3 years. |
| `ambr-py` | | **GPL-3.0** | **DO NOT VENDOR** - same reason. See the ADR-006 note below. |

> **ADR-006 dissolves exactly one objection in this table and no others.** This
> tree is now GPL-3.0-or-later, so the reason this table used to give - that
> "copyleft would relicense this repo" - is no longer true of `enka-py` or
> `ambr-py`. That objection is void. The refusal is not, and it stands
> unchanged: the blanket caveat below is untouched and is why neither is
> vendored. A licence on a wrapper cannot grant rights to HoYoverse's data, and
> the data was always the actual gate. Both were re-verified GPL-3.0 on the
> 2026-09-06 pass.

**Blanket caveat:** every source above wraps HoYoverse-copyright game assets,
stats, text and item names. A permissive licence on the wrapper grants rights to
that author's code and compilation only. It cannot grant rights to the
underlying game data.

**Chosen posture, and it is the only one implemented:**
1. Vendor **no** Genshin data files. `data/fixtures/` holds only hand-authored
   minimal test fixtures, clearly labelled as such.
2. Re-implement the Enka client from the published protocol docs. Protocol facts
   are not copyrightable; source is. This is the path CLAUDE.md already
   prescribes and it is the only always-legal one.
3. Fetch at runtime with a custom User-Agent, honour the response `ttl`, and
   never enumerate UIDs.

### Enka client policy, from the official docs
- A custom `User-Agent` header is **required by policy**.
- Rate limits are dynamic; overspeed degrades then returns **429**.
- Every UID response carries `ttl` = seconds until the next Showcase refresh.
  Cached data is returned until expiry **and still burns your rate limit**, so
  the client must suppress requests until `ttl` expires.
- Error codes to handle: 400 bad UID, 404 player absent, 424 maintenance,
  429 rate-limited, 500/503 server.
- Explicit prohibition: "don't try to enumerate UIDs or try to do massive query
  jobs in an effort to fill a database."

## 5. VERIFIED Enka payload shape

The brief's URL `https://enka.network<uid>` is malformed. Real endpoints:
```
https://enka.network/api/uid/{uid}/          full: playerInfo + avatarInfoList
https://enka.network/api/uid/{uid}/?info     playerInfo only, much faster
```

Field verdicts, from `EnkaNetwork/API-docs/docs/gi/api.md`:

| Field | Status | Trap |
|---|---|---|
| `playerInfo` | CONFIRMED | nickname, signature, worldLevel, namecardId, finishAchievementNum, towerFloorIndex, towerLevelIndex |
| `avatarInfoList` | CONFIRMED | **absent entirely** if the showcase is closed or empty. Not `[]`. |
| `avatarId` | CONFIRMED | the docs TABLE misprints it as `avatarID`. The wire key is `avatarId`. |
| `propMap` | CONFIRMED | `{type: {type, ival, val}}`. 1001=XP, 1002=Ascension, 4001=Level. `ival` is documented as "Ignore it". |
| `talentIdList` | CONFIRMED | **the key is MISSING at C0**, not `[]`. `len(avatar["talentIdList"])` raises KeyError. Always `.get("talentIdList", [])`. |
| `skillLevelMap` | CONFIRMED | **does NOT include constellation-granted +3 levels.** Those live in `proudSkillExtraLevelMap`, a real field the docs table omits. A talent-level reader that ignores it is wrong for any C3+ character, and wrong in the direction that matters - it under-reports invested talent. **See 5.1: the fold is not always possible.** |
| `equipList` | CONFIRMED | `{itemId, weapon|reliquary, flat}` |
| `flat` | CONFIRMED | nameTextHashMap, setNameTextHashMap, rankLevel, reliquaryMainstat, reliquarySubstats, weaponStats, itemType, icon, equipType |
| `itemType` | CONFIRMED | exactly `ITEM_RELIQUARY` and `ITEM_WEAPON` |
| `reliquarySubstats` | CONFIRMED | under `flat`, artifact only, `[{appendPropId, propValue}]` |
| `affixMap` | **MISPLACED IN BRIEF** | it is NOT top-level and NOT under `flat`. It is `equipList[].weapon.affixMap`, and it is weapon refinement with documented range **0..4**, i.e. R1..R5 minus one. |

Also real and worth mapping: `fightPropMap`, `skillDepotId`,
`inherentProudSkillList`, `fetterInfo.expLevel`, `costumeId`, top-level `owner`
and `ttl`.

### 5.1 CORRECTION - the talent fold is not always resolvable

This spec originally said to "populate `talent_levels` as the EFFECTIVE level with
those bonuses already folded in", as though the fold were a simple lookup. Slice E
found it is not, and the reason is structural:

**`proudSkillExtraLevelMap` is keyed by `proudSkillGroupId`, not by `skillId`.**
`skillLevelMap` is keyed by `skillId`. Joining the two requires the character's
skill depot, which is exactly the kind of bulk game data ADR-002 forbids vendoring.

So a correct mapper cannot always fold. The implemented resolution order, most
trustworthy first:

1. An explicit `skill_group_map` (proudSkillGroupId -> skillId) supplied by the
   caller. The only exact answer for a live payload.
2. An exact key hit, when a bonus key is already present in `skillLevelMap`.
3. A positional pairing of sorted keys. **DEFAULT-OFF**, because inventing a
   numeric relation between a proudSkillGroupId and a skillId is scaffolding on
   an assumption.

Anything unresolved is **RETURNED** as a third value rather than dropped or
guessed, so a caller can see what it did not get. `fold_talent_levels` therefore
returns `(effective_levels, base_levels, unresolved_bonuses)`.

This is a real product limitation, not an implementation shortcut: without a
licensed skill-depot source, constellation talent bonuses on a live profile are
resolvable only when the caller supplies the mapping. Recorded in ROADMAP.

### Verified avatarIds for the seed roster

| Character | avatarId | Note |
|---|---|---|
| Arlecchino | **10000096** | brief's claim CONFIRMED by two independent sources |
| Dehya | **10000079** | |
| Lynette | **10000083** | internal name `Linette` |
| Bennett | **10000032** | |
| Noelle | **10000034** | internal icon name `Noel` |

Refuted along the way, do not reintroduce: `10000088` is Charlotte, not Dehya.
`10000080` is Mika, not Lynette.

### Verified boss materials

- **Fragment of a Golden Melody**, item id **113059**. Arlecchino ascension
  (`ascend2` takes 2). Also used by Emilie. Boss: Legatus Golem, Fontaine.
- **Light Guiding Tetrahedron**, item id **113039**. Used by **Candace, Dehya,
  Faruzan**. **NOT Arlecchino** - the brief pairs it with Arlecchino, which is
  wrong. Boss: Algorithm of Semi-Intransient Matrix of Overseer Network, Sumeru.

## 6. Slice boundaries

Slices write ONLY inside their own paths. No slice edits another slice's files.
`core/types.py` is written by the orchestrator BEFORE fan-out and is READ-ONLY
to every slice.

| Slice | Owns | Must not touch |
|---|---|---|
| A hygiene | `ruff.toml` `pytest.ini` `mypy.ini` `conftest.py` `requirements*.txt` `.gitignore` `.gitattributes` `.githooks/**` `.github/**` `scripts/install_hooks.py` `scripts/precommit_*.py` `tools/precommit_gate.py` | everything else |
| B engine | `agents/pity_engine/**` | everything else |
| C economy | `core/ledger.py` `core/resin.py` `core/domains.py` `core/atomic_io.py` `core/log_setup.py` `core/config.py` `tests/test_core_*.py` | `core/types.py` |
| D planner | `engines/**` `tests/test_engines_*.py` | everything else |
| E ingest | `ingest/**` `scripts/bootstrap_data.py` `data/fixtures/**` `tests/test_ingest_*.py` | everything else |
| F headless | `headless/**` `ops/**` `tests/test_headless_*.py` | everything else |
| G docs | `README.md` `CLAUDE.md` `ROADMAP.md` `docs/**` except this file | everything else |

## 7. Acceptance

A slice is done when, from the repository root:
1. `python -m py_compile` passes on every `.py` it wrote.
2. `python -m ruff check .` reports zero findings on its files.
3. `python -m pytest <its own test paths> -q` is green, with the observed count
   reported.
4. No banned glyph appears in anything it wrote (`tools/precommit_gate.py`).
5. Every external field, endpoint and item id it relies on appears in section 3,
   4 or 5 above. Nothing is invented.
