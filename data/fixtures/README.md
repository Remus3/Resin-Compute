# data/fixtures - SYNTHETIC test data only

Everything in this directory is **hand-authored by this repository** for tests
and for the offline bootstrap path. **No upstream dataset is vendored here, and
none ever will be.** If you are about to add a bulk data dump, stop and read
section 4 of `docs/SPEC_SCAFFOLD.md` first.

ASCII only in this directory - no em-dashes, no en-dashes, no smart quotes.

## Why nothing is vendored

Verified 2026-09-06 against the primary sources. Summary of the license gate:

| Source | Status | Verdict |
|---|---|---|
| `Dimbreath/GenshinData` | GitHub repo is **404, DMCA'd 2022**. The live successor carries **no LICENSE file at all**. | DO NOT VENDOR. Do not even design an ingest path against it. The dead URL is deliberately not written down here. |
| `genshin-db` | The **code** is MIT (`Copyright (c) 2020 theBowja`). Its own readme says the **data** comes from the Fandom wiki (CC BY-SA 3.0) and from GenshinData. | Code is clear, the payload is not. The MIT badge does NOT clear the data. No bulk data lifted. |
| Enka `API-docs` | **No LICENSE file.** | Protocol facts (endpoint shapes, field names, status codes) are usable - facts are not copyrightable. Its `store/*.json` is fetch-only and is NOT vendored. |
| `enka-py` (pypi `enka`) | **GPL-3.0** | DO NOT VENDOR. Copyleft would relicense this repository. |
| `ambr-py` | **GPL-3.0** | DO NOT VENDOR, same reason. |
| Project Amber | Real base URL is `https://gi.yatta.moe/api/v2` (not `ambr.top`). No published terms, no published rate limits. | Fetch at own risk, treat as unstable, vendor nothing. |

Blanket caveat that survives all of the above: every one of those projects wraps
HoYoverse-copyright game assets, stats, text and item names. A permissive
license on the wrapper grants rights to that author's own code and compilation.
It cannot grant rights to the underlying game data.

**Chosen posture, and the only one implemented:** the Enka client in
`ingest/enka_client.py` is re-implemented from the published protocol, fetches at
runtime with a custom User-Agent, honours the response `ttl`, and never
enumerates UIDs. Identity data lives here, hand-authored, minimal, and limited to
ids that were independently verified.

## Files

### `seed_roster.json`

The five verified seed characters and nothing else. Loaded by
`ingest/static_data.py`, which is the ONLY place character identity lives.

| Character | avatarId | Element |
|---|---|---|
| Arlecchino | 10000096 | Pyro |
| Dehya | 10000079 | Pyro |
| Lynette | 10000083 | Anemo |
| Bennett | 10000032 | Pyro |
| Noelle | 10000034 | Geo |

**Refuted during verification - do not reintroduce:**

- `10000088` is **Charlotte**, NOT Dehya.
- `10000080` is **Mika**, NOT Lynette.

Both wrong ids were proposed and then refuted on 2026-09-06. They are recorded
in the `_refuted` block of the JSON as well, so the correction travels with the
data rather than only with this README.

Unknown ids are NOT an error. `static_data.character_name` returns a stable
placeholder of the form `unknown:10000123` and never raises, never guesses a
name. Adding a sixth character requires an independently verified avatarId.

### `seed_materials.json`

The two verified boss materials.

| Material | id | Used by | Boss | Region |
|---|---|---|---|---|
| Fragment of a Golden Melody | 113059 | Arlecchino, Emilie | Legatus Golem | Fontaine |
| Light Guiding Tetrahedron | 113039 | Candace, Dehya, Faruzan | Algorithm of Semi-Intransient Matrix of Overseer Network | Sumeru |

**Correction, recorded so it is not reintroduced:** the original brief paired
**Light Guiding Tetrahedron with Arlecchino**. That is **wrong**. Light Guiding
Tetrahedron is used by Candace, Dehya and Faruzan, and is not an Arlecchino
material. Arlecchino's boss material is Fragment of a Golden Melody (113059).
The same correction is carried in the `_corrections` block of the JSON itself.

### `enka_sample_profile.json`

A small SYNTHETIC payload, hand-authored, shaped exactly like a real profile
response. It exists to exercise every verified upstream trap in one file:

1. **Bennett (10000032) has no `talentIdList` key at all.** That is the real C0
   state - the key is MISSING, not empty. `len(avatar["talentIdList"])` raises
   `KeyError`. The mapper uses `.get("talentIdList", [])`.
2. **`propMap` 4001 carries `ival` 0 next to `val` 80.** `ival` is documented as
   "Ignore it". A reader that trusts it reports level 0, which is why the values
   deliberately disagree here.
3. **Arlecchino (10000096) carries `proudSkillExtraLevelMap`.** `skillLevelMap`
   does NOT include constellation-granted +3 talent levels; they live in that
   separate map. The mapper folds them into the effective level.
4. **`affixMap` sits at `equipList[].weapon.affixMap`** - not top level, not
   under `flat`. Arlecchino's weapon carries 4, so presented refinement is 5;
   Noelle's carries 0, so presented refinement is 1.
5. **An `ITEM_RELIQUARY` with `flat.reliquarySubstats`** as
   `[{appendPropId, propValue}]`.
6. The wire key is `avatarId`. The docs table misprint `avatarID` appears
   nowhere in this fixture, deliberately.

Only the avatarIds in this file are real, and only the five verified ones. Every
other id is a deliberately unrealistic placeholder in the 9xxxxxxx range, and
every name hash and prop id is a `SYNTHETIC_*` string, so no value here can be
mistaken for or reused as game data. In a live payload the
`proudSkillExtraLevelMap` keys are proudSkillGroupIds that need the character
skill depot to resolve; this fixture keys them by a skill id already present in
`skillLevelMap` so the fold is exercised without vendoring depot data. The
mapper accepts an explicit `skill_group_map` for the live case.
