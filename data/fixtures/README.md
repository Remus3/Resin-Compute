# data/fixtures - hand-authored test data, nothing vendored

Everything in this directory is **hand-authored by this repository** for tests
and for the offline bootstrap path. **No upstream dataset is vendored here, and
none ever will be.** If you are about to add a bulk data dump, stop and read
section 4 of `docs/SPEC_SCAFFOLD.md` first.

**Two different kinds of file live here, and the difference is the point.**
`seed_roster.json` and `seed_materials.json` are hand-authored records of
publicly known game FACT - real avatarIds and real material ids, independently
verified and typed in one row at a time rather than lifted from a dataset.
`enka_sample_profile.json` is the other kind: a synthetic payload whose ids and
name hashes are deliberate placeholders corresponding to nothing real. Both
kinds are hand-authored. Only the third file is synthetic, and each file states
which kind it is in its own header block.

This heading used to read "SYNTHETIC test data only", which was false of two of
the three files, and the two seed tables carried a `"_synthetic": true` flag on
the line directly above a note calling them hand-authored tables of verified
ids. Synthetic means INVENTED, and a verified avatarId is not invented. The
labels now say what the files are, because this README is what a takedown
correspondent gets pointed at and a compliance document that is demonstrably
false about its own contents is a far worse position than the true one. Here the
true claim is also the stronger one: nothing in this repository is vendored at
all.

ASCII only in this directory - no em-dashes, no en-dashes, no smart quotes.

## Why nothing is vendored

Verified 2026-09-06 against the primary sources. Summary of the license gate:

> **ADR-006 dissolves exactly one objection in the table below, and no others.**
> This tree is now GPL-3.0-or-later, so "vendoring a GPL-3 library would
> relicense this repository" stopped being true of `enka-py` and `ambr-py`. That
> reason is dead, and it is marked dead wherever it appears rather than left
> standing for a reader to check and find void.
>
> **The refusal itself stands, on the reason that always mattered.** Both
> projects wrap HoYoverse game data, and a licence on a wrapper cannot grant
> rights to the payload underneath it. The blanket caveat below this table is
> untouched and is the operative reason. The data was always the actual gate,
> and no outbound licence decision of ours can move it. Same finding, same
> shape, as the header of `docs/LICENSE_NOTES.md`.

| Source | Status | Verdict |
|---|---|---|
| `Dimbreath/GenshinData` | GitHub repo is **404, DMCA'd 2022**. The live successor carries **no LICENSE file at all**. | DO NOT VENDOR. Do not even design an ingest path against it. The dead URL is deliberately not written down here. |
| `genshin-db` | The **code** is MIT (`Copyright (c) 2020 theBowja`). Its own readme says the **data** comes from the Fandom wiki (CC BY-SA 3.0) and from GenshinData. | Code is clear, the payload is not. The MIT badge does NOT clear the data. No bulk data lifted. |
| Enka `API-docs` | **No LICENSE file.** | Protocol facts (endpoint shapes, field names, status codes) are usable - facts are not copyrightable. Its `store/*.json` is fetch-only and is NOT vendored. |
| `enka-py` (pypi `enka`) | **GPL-3.0** | DO NOT VENDOR - but NOT for the copyleft, which ADR-006 dissolved. It wraps HoYoverse game data, and no licence on the wrapper reaches the payload. |
| `ambr-py` | **GPL-3.0** | DO NOT VENDOR, on that same surviving reason: the wrapper's licence cannot clear the game data it carries. ADR-006 dissolved the copyleft objection and nothing else. |
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

**Kind: hand-authored record of publicly known fact.** The ids below are real
and were independently verified before they were typed in. The file's own
`_hand_authored` and `_vendored` flags say so, and its `_content` block spells
out what that means.

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

**Kind: hand-authored record of publicly known fact,** on the same footing as
the roster table. Real material ids, independently verified, typed in by hand.
The same `_hand_authored`, `_vendored` and `_content` header block applies.

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

**Kind: genuinely SYNTHETIC.** This is the one file in the directory whose
contents are invented, it carries `"_synthetic": true` truthfully, and that
label must not be swept away with the two false ones.

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
