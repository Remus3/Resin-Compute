# Third-party data posture

Read this before adding any external data source, library or dataset. Verified
2026-09-06 against primary sources. Inherited from Sibling-C's third-party
lift rule.

> **This file answers the INBOUND question only:** what may this project
> consume? The OUTBOUND question - what may others do with this project - is
> answered by `LICENSE` (GPL-3.0-or-later) and recorded in ADR-006. They are
> different questions and the answer to one constrains the other only in the one
> respect ADR-006 sets out.
>
> **ADR-006 dissolves exactly one objection below and no others.** This tree is
> now GPL-3-or-later, so "vendoring a GPL-3 library would relicense this repo"
> is no longer true of `enka-py` or `ambr-py`. The blanket caveat at the end of
> this file is untouched and is the reason those projects still are not
> vendored: a licence on a wrapper cannot grant rights to HoYoverse's data, and
> the data was always the actual gate.

## The rule

Before lifting ANYTHING from an external repo, check the licence and say what it
is. Five traps, all of them real and all of them hit during this project's own
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
5. **A gate that does not run refuses nothing.** This tree vendored
   `docs/CHANNEL.md` from a sibling without ever opening this document, on an
   upstream note that said the source tree was public and named no licence.
   Public is a VISIBILITY, not a grant. A neighbouring tree's licence gate
   caught it; nothing here would have. See the vendored-artifact section
   below.

Copyleft is no longer an automatic bar, and this rule changed with ADR-006. While
this tree was proprietary, "vendoring GPL code would relicense this repo" ended
the argument on its own. This tree is now GPL-3.0-or-later, so incorporating
GPL-3 code is licence-compatible and that objection is void. What replaces it is
narrower and harder: the question becomes what the code CARRIES. Every candidate
in the table below wraps HoYoverse game data, and no licence on a wrapper can
grant rights to that payload - so each one is still DO-NOT-VENDOR, on the reason
that always governed rather than on the one that has now dissolved. A copyleft
licence that is INCOMPATIBLE with GPL-3-or-later, such as a GPL-2-only library,
remains an automatic bar. BUSL-1.1 is source-available rather than copyleft, and
is DO-NOT-VENDOR anyway.

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
| `enka-py` (PyPI `enka`) | `github.com/seriaati/enka-py`, actively maintained | **GPL-3.0**. `pyproject.toml` points `license` at the GPL file, consistent | **DO NOT VENDOR** - it wraps HoYoverse game data. The copyleft objection died with ADR-006; this one did not |
| `enkanetwork.py` | `github.com/mrwan200/EnkaNetwork.py` | MIT, `Copyright 2022 M-307` | Vendorable, but last released 2023-08-30 and effectively unmaintained |
| `ambr-py` | `github.com/seriaati/ambr` | **GPL-3.0** | **DO NOT VENDOR** - same reason. It wraps HoYoverse game data |

The maintained Python Enka client is GPL and the permissive one is stale. That is
why this repo re-implements a minimal client instead of taking either.

## Blanket caveat

Every source above wraps **HoYoverse-copyright game assets, stats, text and item
names**. A permissive licence on the wrapper grants rights to that author's own
code and compilation only. It does not and cannot grant rights to the underlying
Genshin Impact data.

## Vendored third-party artifacts, and their provenance

Three tracked files here were authored elsewhere and copied in byte-wise.
Everything else under version control in this tree is this project's own work.
Each row records what Apache-2.0 section 4 makes a redistributor answerable
for - which notices arrived with the file, whether the bytes were changed, and
who is to be attributed.

| Vendored path | Upstream | Inbound licence | SPDX | Copyright holder | Bytes changed here |
|---|---|---|---|---|---|
| `docs/CHANNEL.md` | Sibling-C, the tree this project's blueprint comes from (ADR-001); channel initials RC | Apache License 2.0 | `Apache-2.0` | Moonbeam | **None.** Byte-identical to upstream |
| `ops/loop/slots.py` | Sibling-E, channel initials LW | Apache License 2.0 | `Apache-2.0` | Moonbeam | **None.** Byte-identical to upstream |
| `ops/loop/winmutex.py` | Sibling-E, channel initials LW | Apache License 2.0 | `Apache-2.0` | Moonbeam | **None.** Byte-identical to upstream |

Every licence fact above was read from the upstream tree's own `LICENSE` file on
this host, not from a hand-off note. Sibling-C's is 219 lines, opening "Apache
License" then "Version 2.0, January 2004", with a RENDERED grant - the copyright
line names Moonbeam rather than leaving a template placeholder, which is trap 2
above and the thing that most often turns out to be missing. Sibling-E's is the
same licence at 202 lines with the same rendered holder. The upstream repository
is public: its visibility was confirmed from the unauthenticated GitHub API,
which reports the repository as not private.

Sibling-C's `LICENSE` also carries a SCOPE OF THIS LICENSE block stating that
the Apache grant covers that repository's source code AND its authored
documentation, and excludes only the third-party-sourced data files under its
own `data/` directory, which keep their upstream terms and are recorded in that
tree's NOTICE source by source. Its README says the same. `docs/CHANNEL.md` is
authored documentation, is not under that tree's `data/`, and carries no
per-file exception anywhere - no SPDX header, no licence or copyright line
inside it, and no per-directory licence file over `docs/`. So it is covered.

### Where each pin lives, and what it is a digest of

- `docs/CHANNEL.md` - LF-normalised sha256
  `899f6eb957cc26ee25993d83d65d8ca291841fe4eec24a48f729c2dc005f4c6b`, 20633
  bytes, zero CR. Pinned by `tests/test_channel_doc_pin.py`. The digest is taken
  over LF-normalised bytes so a checkout that lands CRLF is not red while every
  git blob is identical; this tree pins markdown to LF anyway, so raw and
  normalised agree here.
- `ops/loop/slots.py` - sha256
  `71fa2a683f2eaa04dd61feb2bebc646b5f9086e692c5acc05a9239de49d07d1b`.
- `ops/loop/winmutex.py` - sha256
  `0b112a4f6bfa88cf5f537f8869225c1821ebfe97428b1e899979797ddd71a61e`.
  Both loop modules are pinned by `tests/test_loop_concurrency.py`, and
  re-pinning either is a joint act across every carrier rather than a local
  checksum regeneration.

### Attribution cannot live inside these files, and two separate rules say so

The ordinary place for an attribution header is the top of the vendored file.
That is unavailable for all three of these, and not as a matter of taste:

1. **The bytes are a fleet-wide pin.** Several repositories carry each of these
   files at the same relative path and coordinate THROUGH them - the channel doc
   is the convention every carrier reads, and the loop modules coordinate through
   an on-disk protocol and a kernel-object namespace. One added comment line
   changes the digest, desynchronises every carrier that has not moved, and in
   the loop modules' case is a silent concurrency bug rather than a merge
   conflict anybody notices. So the attribution has to sit BESIDE the file, and
   this document is where it sits.
2. **Apache-2.0 section 4 does not ask for a header anyway.** It asks a
   redistributor to give recipients a copy of the licence, to mark modified
   files as changed, to retain the notices the source form already carried, and
   to carry forward attribution. Nothing here was modified, so the
   mark-your-changes clause has nothing to attach to - and that is a fact worth
   writing down rather than inferring from the absence of a marker.

### Why no repository URL appears in this section

This repository is public, and `tests/test_no_sibling_names.py` refuses any
tracked file that names a sibling project of the same operator's in plain text.
Both upstream project names, and therefore both clone URLs, are exactly what
that sweep exists to keep out of a public tree. Writing them here would turn the
sweep red, and spelling them so the sweep cannot see them would hide the pattern
from the next reader as well, which that guard's own notes refuse.

The codenames above are the citable form. They resolve only in the gitignored
per-host file ops/moon_sync_repos.json - deliberately left unbackticked, because
a backticked path is checked for trackedness by `tests/test_docs_consistency.py`
and this one is tracked nowhere by design.

This is a real cost and it should be stated as one: a downstream recipient of
ResinCompute cannot reach the upstream repository from this file alone. What
they CAN do is what Apache-2.0 section 4 actually requires - identify the
licence, identify the copyright holder, and see that the bytes are unmodified.
The holder is named. The holder is the same person who holds the copyright in
this tree, which is why the attribution and the licence identification are
satisfiable without the project name.

### The compatibility direction, stated as a direction

Inbound `Apache-2.0` into an outbound `GPL-3.0-or-later` tree. This is
ONE-WAY-COMPATIBLE and the direction is the whole of the answer:

- **Apache-2.0 into GPL-3.0-or-later: permitted.** GPLv3 was drafted to accept
  Apache-2.0's patent and indemnity terms, which GPLv2 could not. The combined
  work ships under this tree's outbound `LICENSE` - confirmed from that file
  itself, which is the verbatim GNU General Public License Version 3 and whose
  how-to-apply block reads "either version 3 of the License, or (at your option)
  any later version". The vendored files keep their own inbound terms as
  recorded here.
- **The reverse does not hold.** Nothing in this tree may travel back upstream
  under Apache-2.0, and a GPL-3.0-ONLY outbound would not have accepted these
  files at all. That is why the `or-later` is load-bearing rather than
  decorative, and ADR-006 is where the outbound decision itself is recorded.

What that leaves this tree responsible for, per Apache-2.0 section 4:

| Section 4 obligation | Met where |
|---|---|
| Give recipients a copy of the Apache licence | The full text is not vendored here; this section identifies the licence by name and SPDX id, and the upstream `LICENSE` is the authoritative copy |
| Mark changed files as carrying changes | Nothing to mark. All three files are byte-identical to upstream, and the digests above are how a reader checks that rather than taking it on trust |
| Retain the notices present in the source form | None of the three carries a per-file copyright, licence or SPDX header upstream; the grant is the repository-level `LICENSE`. There was nothing to strip and nothing was stripped |
| Carry forward attribution | The copyright holder is named in the table above, and the holder is the same in both trees |

The first row is the one a strict reader may want tightened - the safest version
is to vendor the Apache-2.0 text alongside. It is not done today, and saying so
is better than implying a completeness this section does not have.

### The process finding, which is the part worth keeping

**This tree vendored `docs/CHANNEL.md` without running its own inbound gate, and
a sibling's gate is what caught the omission.** The sequence, because the shape
of it is reusable:

1. The upstream note proposing the file named a commit and called the tree
   public. **Public is a visibility, not a grant.** It named no licence at all.
2. Four trees were asked to carry the bytes. This one did, and never opened this
   document on the way past - so the five traps above were never applied to it.
3. Sibling-D refused the file at its own licence gate on exactly that basis. That
   refusal was correct and it still stands until that tree acts on the concession.
4. The upstream author has since conceded the omission plainly and named the
   licence. The table above is not built from that concession: every fact in it
   was re-read from the upstream `LICENSE` on disk.

The defect was never the licence, which turned out to be clean. The defect was
that a gate this repository already owned did not run, and nothing in the tree
would have noticed. A vendoring event has to route through this document BEFORE
the bytes land, not after a neighbour asks. `tests/test_vendored_provenance.py`
now asserts that every artifact this tree declares as vendored has a row here,
and it is honest about what it cannot see: a future vendor drop that arrives
with no byte pin at all is outside its reach by construction.

## Chosen posture, as implemented

1. **Vendor no game data.** `data/fixtures/` is HAND-AUTHORED, and no upstream
   dataset is vendored into it. TWO KINDS of file live there and the difference
   is the point. `seed_roster.json` and `seed_materials.json` are records of
   publicly known game FACT - real avatarIds and material ids, independently
   verified and typed in one row at a time rather than lifted from a dataset;
   both carry `_hand_authored: true` and `_vendored: false`. Only
   `enka_sample_profile.json` is genuinely synthetic: its ids and name hashes
   are deliberately unrealistic placeholders that could not be mistaken for
   game data, and it carries `_synthetic: true`. Each file is labelled with its
   own kind in `data/fixtures/README.md`.

   An earlier draft of this bullet called the whole directory synthetic, which
   the sibling file it cited as its own authority declares false. SYNTHETIC
   MEANS INVENTED, and a verified avatarId is not invented. Hand-authored is
   what ADR-002 requires, and it is also the STRONGER claim: nothing was lifted
   from anywhere at all. Corrected 2026-09-06 and guarded in
   `tests/test_licence_posture.py`.
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

No HoYoverse-coined proper noun appears as a module name, package name, class
name or CLI verb in this repo. That is the claim, and it is the whole of it.

**It does not extend to every identifier, and an earlier draft of this section
said it did.** That draft read "game data values such as character and item names
appear only as data, never as code identifiers", which is false of this tree:
`CurrencyKind` in `core/types.py` has `PRIMOGEM`, `INTERTWINED_FATE`,
`STARGLITTER` and `HEROS_WIT` among its MEMBER NAMES, and those are code
identifiers naming HoYoverse-coined items. Overclaiming here costs more than it
buys - a compliance sentence a reader can falsify in one grep discredits the
sentences around it that are true.

The narrow claim is the defensible one, and it is the one this project actually
holds to. Referring to an item by its name in order to talk about it is
nominative use, which is ordinary and expected of a fan tool; what matters is
that the PROJECT and its public surface are not named after someone else's
marks. `docs/SPEC_SCAFFOLD.md` section 0 states the same narrow claim, and the
naming decisions below are how it was met.

Names considered and rejected for the project itself, with reasons, so the
question is not reopened: `GenshinOps` and `impact-commander` use the registered
mark directly. `TeyvatLane`, `AkashaRunner`, `IrminsulDB` and `KhemiaOS` all use
HoYoverse-coined or HoYoverse-appropriated lore proper nouns, which is worse for
compliance rather than better. `ResinCompute` and `PityEngine` were chosen because
"resin" is a generic English word and "pity" is a generic gacha-community term,
and neither is a HoYoverse mark.
