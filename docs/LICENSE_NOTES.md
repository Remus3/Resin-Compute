# Third-party data posture

Read this before adding any external data source, library or dataset. Verified
2026-09-06 against primary sources. Inherited from Riot Commander's third-party
lift rule.

## The rule

Before lifting ANYTHING from an external repo, check the licence and say what it
is. Four traps, all of them real and all of them hit during this project's own
verification pass:

1. **A repo can contradict itself.** The `LICENSE` file and the `package.json`
   or `pyproject.toml` licence field can disagree. Read both.
2. **A LICENSE file can name nobody.** An unrendered template reading
   `Copyright (c) {{ year }} {{ organization }}` is a grant with no grantor. Read
   the copyright LINE, not just the licence name.
3. **A permissive wrapper does not clear its payload.** An MIT licence covers
   that author's code and compilation. It cannot grant rights to data the author
   scraped from a CC BY-SA wiki or from datamined game files.
4. **The person who cleared it may not own it.** A repo crediting prior authors
   has multiple copyright holders and its maintainer cannot unilaterally
   relicense it.

GPL and other copyleft stays DO-NOT-VENDOR regardless of verbal clearance, because
vendoring it would relicense this repo. BUSL-1.1 is source-available, not
copyleft, and is DO-NOT-VENDOR anyway.

The always-legal path is the one this repo already uses: re-implement the
mechanic from observed behaviour and published protocol. Techniques and protocol
facts are not copyrightable. Source is.

## Verified findings

| Source | Real location | Licence | Verdict |
|---|---|---|---|
| GenshinData | `github.com/Dimbreath/GenshinData` returns **404, DMCA'd 2022**. Live successor `gitlab.com/Dimbreath/animegamedata2` | **NONE.** No LICENSE file, no copyright line, on any of the three known mirrors | **DO NOT VENDOR. Not an ingest target.** A README asking for credit is not a licence. Many downstream repos say "data from GenshinData" and inherit this problem silently |
| genshin-db | `github.com/theBowja/genshin-db`, npm `genshin-db` | MIT, `Copyright (c) 2020 theBowja`, manifest agrees, no contradiction | **Code MIT. Bulk data NO.** Its own readme states the data is sourced from the Fandom wiki (**CC BY-SA 3.0**, share-alike) and from GenshinData. The MIT badge covers theBowja's code and compilation, not the payload |
| Enka API docs | `github.com/EnkaNetwork/API-docs` | **NONE** | Protocol facts usable. `store/*.json` is **fetch-only, do not vendor** |
| Project Amber | base URL is **`https://gi.yatta.moe/api/v2`**. `ambr.top` is the legacy name | **NONE**, and no published terms or rate limits | Fetch at own risk. Treat as unstable. Do not vendor |
| `enka-py` (PyPI `enka`) | `github.com/seriaati/enka-py`, actively maintained | **GPL-3.0**. `pyproject.toml` points `license` at the GPL file, consistent | **DO NOT VENDOR.** Copyleft would relicense this repo |
| `enkanetwork.py` | `github.com/mrwan200/EnkaNetwork.py` | MIT, `Copyright 2022 M-307` | Vendorable, but last released 2023-08-30 and effectively unmaintained |
| `ambr-py` | `github.com/seriaati/ambr` | **GPL-3.0** | **DO NOT VENDOR** |

The maintained Python Enka client is GPL and the permissive one is stale. That is
why this repo re-implements a minimal client instead of taking either.

## Blanket caveat

Every source above wraps **HoYoverse-copyright game assets, stats, text and item
names**. A permissive licence on the wrapper grants rights to that author's own
code and compilation only. It does not and cannot grant rights to the underlying
Genshin Impact data.

## Chosen posture, as implemented

1. **Vendor no game data.** `data/fixtures/` holds only hand-authored synthetic
   fixtures for tests, labelled as such in `data/fixtures/README.md`.
2. **Re-implement the client** from the published protocol in
   `ingest/enka_client.py`. No upstream client source is copied.
3. **Fetch at runtime**, with a custom User-Agent, honouring the response `ttl`,
   and never enumerating UIDs.

## Enka.Network usage policy, as published

These are upstream's stated rules and the client enforces them in code, not just
in prose:

- A custom `User-Agent` header is **required**. The client refuses to send a
  default and errors with the config key to set.
- Rate limits are **dynamic**. Exceeding them degrades response time and then
  returns **429**.
- Every UID response carries `ttl`, the seconds until the next Showcase refresh.
  Cached data is served until it expires **and still burns your rate limit**, so
  suppressing requests inside the window is mandatory, not an optimization.
- Status codes to handle: 400 bad UID, 404 player absent, 424 maintenance,
  429 rate-limited, 500 and 503 upstream error.
- Explicit prohibition, quoted: "don't try to enumerate UIDs or try to do massive
  query jobs in an effort to fill a database."

Real endpoints:

```
https://enka.network/api/uid/{uid}/          full profile
https://enka.network/api/uid/{uid}/?info     playerInfo only, much faster
```

The form `https://enka.network<uid>` that appeared in this project's originating
brief is malformed and does not exist.

## Trademark posture

No HoYoverse-coined proper noun appears as a module, package, class or CLI
identifier in this repo. Game data values such as character and item names appear
only as data, never as code identifiers.

Names considered and rejected for the project itself, with reasons, so the
question is not reopened: `GenshinOps` and `impact-commander` use the registered
mark directly. `TeyvatLane`, `AkashaRunner`, `IrminsulDB` and `KhemiaOS` all use
HoYoverse-coined or HoYoverse-appropriated lore proper nouns, which is worse for
compliance rather than better. `ResinCompute` and `PityEngine` were chosen because
"resin" is a generic English word and "pity" is a generic gacha-community term,
and neither is a HoYoverse mark.
