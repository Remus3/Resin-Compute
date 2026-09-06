# ADR-002: Vendor no game data; re-implement the Enka client from protocol

**Status:** Accepted, 2026-09-06

> **AMENDED by `docs/adr/ADR-006-outbound-licence.md` in exactly one respect,
> 2026-09-06. The body below is left exactly as it was written.**
>
> **DISSOLVED:** the Context below gives, as one reason to refuse `enka-py` and
> `ambr-py`, that "Vendoring either would relicense this repo." That was true of
> a permissive or unlicensed tree. This tree is now GPL-3.0-or-later, so
> incorporating GPL-3 code relicenses nothing that is not already so licensed.
> Both projects were re-verified as GPL-3.0 on 2026-09-06.
>
> **ADR-006 dissolves that one objection and no others.** In particular, **the
> refusal itself stands unchanged.** Both projects wrap HoYoverse-copyright game
> data, and a licence on a wrapper cannot grant rights to the payload. The data
> was always the actual gate, so nothing below becomes vendorable on the strength
> of ADR-006 alone.
>
> The body is not rewritten. An ADR records a decision as it was made; editing
> the reasoning to match a later decision destroys the record this directory
> exists to keep. `docs/LICENSE_NOTES.md` carries the same amendment in the same
> shape.

## Context

The originating brief named four data sources to "bootstrap from and periodically
re-sync with": GenshinData, genshin-db, the Enka.Network API, and Project Amber.
Three of the four URLs it gave were wrong or dead, and a licence verification pass
found that none of them is safe to vendor.

Findings, verified against primary sources on 2026-09-06 and recorded in full in
`docs/LICENSE_NOTES.md`:

- `github.com/Dimbreath/GenshinData` returns **404**. It was DMCA'd in 2022. Its
  live successor at `gitlab.com/Dimbreath/animegamedata2` carries **no LICENSE
  file and no copyright line at all** on any known mirror. A README asking for
  credit is not a licence.
- `genshin-db` is genuinely MIT with a real copyright line, and its manifest
  agrees with its LICENSE file, so it passes the contradiction check. But its own
  readme states the data is sourced from the Fandom wiki, which is **CC BY-SA
  3.0** and therefore share-alike, and from GenshinData, which is unlicensed. The
  MIT grant covers the author's code and compilation, not the payload.
- The Enka API-docs repo carries **no licence**, so its bundled `store/*.json` is
  fetch-only.
- Project Amber's real base URL is `https://gi.yatta.moe/api/v2`, not the
  `ambr.top` the brief gave, and it publishes no terms and no rate limits.
- The maintained Python Enka client, `enka-py`, is **GPL-3.0**. So is `ambr-py`.
  Vendoring either would relicense this repo. The one permissively licensed client,
  `enkanetwork.py`, has not shipped a release since 2023-08-30.

Above all of that sits a blanket problem: every one of these wraps
HoYoverse-copyright game assets, stats and text. A permissive licence on the
wrapper cannot grant rights to the underlying game data.

## Decision

1. **Vendor no game data.** `data/fixtures/` contains only hand-authored synthetic
   fixtures for tests, labelled as synthetic.
2. **Re-implement a minimal Enka client** from the published protocol
   documentation, in `ingest/enka_client.py`. No upstream client source is copied.
   Protocol facts are not copyrightable; source is.
3. **Fetch at runtime** rather than caching a dataset into the repo, with upstream
   policy enforced in code: a required custom User-Agent, `ttl` honoured on every
   response, and a refusal to enumerate UIDs.
4. **GenshinData is not an ingest target at all**, dead or alive.

## Consequences

- The repo carries no licence contamination and no DMCA exposure.
- Character and material identity comes from a small verified seed set in
  `data/fixtures/`, not a bulk import. Unknown ids resolve to a stable placeholder
  such as `unknown:10000123` rather than raising or inventing a name.
- Any future bulk-data need is a new decision requiring its own licence pass.
- If a licensed or first-party data source appears later, this ADR is the place to
  supersede.

## Rejected alternatives

- **Vendor genshin-db's JSON.** Rejected: MIT on the wrapper does not clear a
  CC BY-SA and unlicensed payload.
- **Depend on `enka-py`.** Rejected: GPL-3.0 copyleft.
- **Depend on `enkanetwork.py`.** Rejected: permissively licensed but unmaintained
  for roughly three years, which makes it a liability against a live API.
- **Scrape the Fandom wiki directly.** Rejected: CC BY-SA share-alike, plus it
  still wraps HoYoverse copyright.
