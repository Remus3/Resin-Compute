# ADR-008: Fan-content posture rests on zero vendored assets, not on a permission

**Status:** Accepted
**Date:** 2026-09-06
**Relates to:** ADR-002 (inbound data posture), ADR-006 (outbound licence)

## Context

This repository is a third-party companion for a game it does not ship, does not
modify and does not talk to. Publishing it raises a question neither ADR-002 nor
ADR-006 answers. ADR-002 settles what this project may consume. ADR-006 settles
what others may do with the result. Neither asks what the game publisher's own
published terms say about a project like this one existing at all.

A first version of this ADR answered that question by leaning on a HoYoLAB Legal
FAQ post, and got three checkable things wrong. The corrected version follows,
and the errors are recorded in full at the end because they are the most useful
part of the document.

### The load-bearing facts are about this project, not about a permission

These are properties of the tree, measured 2026-09-06 in a clean worktree, and
each is cheap to re-measure:

- **Zero vendored game assets.** No image, audio, video, font or binary asset is
  tracked anywhere in the repository.
- **Zero vendored game data.** Everything under `data/fixtures/` is
  HAND-AUTHORED, and `data/fixtures/README.md` names which file is which kind.
  Two of the three are verified public game facts - real avatarIds and material
  ids - typed in one row at a time; only `enka_sample_profile.json` is invented,
  and it alone is labelled synthetic. An earlier draft of this bullet called the
  whole directory "synthetic test data", which the sibling file it cited as its
  own authority declares false. Hand-authored is what ADR-002 requires, and it
  is the stronger claim - synthetic means invented, and a verified avatarId is
  not invented. Arms guarded by `tests/test_licence_posture.py`.
- **No contact with the game client.** Nothing reads the game's process, memory,
  installation directory or files. There is no such code path to disable.
- **One outbound host that the application actually fetches.**
  `https://enka.network`, reached from `ingest/enka_client.py`. No COGNOSPHERE or
  HoYoverse endpoint is contacted by any code in this repository.
  STATE THE SCOPE, because a reader will re-run the sweep and must not conclude
  the ADR is wrong. This claim is about CODE PATHS THAT FETCH, not about every
  string in the repository, and the two give very different counts.
  Swept over tracked files under `core/`, `engines/`, `ingest/`, `headless/`,
  `ops/`, `surface/`, `shell/`, `agents/`, `scripts/` and `tools/`, a grep for
  `https?://` returns four hosts. Only `enka.network` is fetched.
  `registry.npmjs.org` and a `github.com/sponsors` link appear solely in
  `shell/package-lock.json`, which is install-time package-manager metadata;
  `schemas.microsoft.com` appears once in `ops/ResinCompute-Supervisor.xml` as an
  XML namespace identifier, which is never dereferenced. Localhost bindings are
  `127.0.0.1` and are owned by `core/ports.py`.
  Sweep ALL tracked files instead and the count rises to roughly thirteen, none
  of them new fetch paths: `gnu.org` and `fsf.org` are inside the verbatim GPL
  text in `LICENSE`, `example.com` and `claude.ai` are fixture strings in
  `tests/`, and `gi.yatta.moe`, `raw.githubusercontent.com` and the two URLs
  cited in this very ADR are prose citations in `.md` files. An earlier draft of
  this bullet said "four hosts across tracked source" without naming the scope,
  and a verification pass correctly refuted it. That was the THIRD claim in this
  ADR to be refuted by re-running it, which is itself the argument for the
  method warning below.
- **The mechanics are re-implemented, not extracted.** Gacha constants come from
  the publisher's own published probability disclosures, cited at the point of
  use. Protocol facts and published numbers are not copyrightable; source and
  assets are.

That list, and not any third-party permission, is what this decision rests on.

### What the published documents actually say

Both documents were retrieved in full and searched as raw bytes rather than
through a summariser.

**COGNOSPHERE Terms of Service**, `https://tot.hoyoverse.com/en-us/terms`,
retrieved 2026-09-06, 219297 bytes.

- **Section 7 clause c contains an express scraping prohibition.** It applies to
  any or all of the COGNOSPHERE Services, which may not be
  "reproduced, republished, downloaded, scraped, displayed, posted, transmitted,
  or sold in any form" without express prior written permission. No
  non-commercial carve-out is attached to it.
- **Section 7 clause a** denies the user any right or interest in in-game
  rewards, achievements, characters and levels, and states that character data
  and game progress may cease to be available at the publisher's sole discretion.
  It is framed as a denial of the user's interest and a reservation of
  discretion, not as an assertion that the publisher owns a player's save. That
  distinction is worth keeping straight when citing it.
- **Section 3, License Conditions clause b, item xi** closes that section's list
  of prohibited acts by prohibiting allowing or assisting third parties to do any
  of them. Verified directly, and the scope matters: that tail closes Section 3's
  own enumeration, items i to x, which run from offensive content through hacking
  to a cross-reference to Section 10. It is not, on its face, attached to Section
  7's list.

**HoYoLAB Legal FAQ**, `https://www.hoyolab.com/article/143107`, retrieved
2026-09-06. Retrieval note for anyone repeating this: the post body lives in the
`structured_content` field of the `getPostFull` response. The `content` field is
five characters long and holds the locale tag, not the body. Anything that reads
`content` and reports the post empty has not read the post.

- **Question 2** asks whether images, text or audiovisual materials may be used
  for re-creation, or posted on a personal fansite. Its answer states that
  non-commercial personal use is not prohibited, then attaches three conditions:
  no rights are transferred, it is not an approval in the legal sense including
  implied approval, and the publisher reserves the right to exercise its rights
  including over derivative works produced and released.
- **Question 7** forbids making or distributing unauthorized game plugins. It
  ends by reserving the right to refuse unauthorized third-party platforms that
  host, disseminate or distribute game plugins and other programs, for any reason
  and at any time. A code-hosting site is a third-party platform. This is a
  reserved right, not a breach claim: exercising it requires no adverse reading
  and no finding of fault.
- **Question 8** answers a private-server question, but its first sentence is
  broader than the question: the publisher does not support or permit the setup
  or provision of any organizations or services relating to its products or
  events. Its second sentence prohibits emulating or redirecting COGNOSPHERE
  Services by protocol emulation, tunneling, modifying game modules,
  "or through the use of any other current or future program or technology", and
  adds that this holds irrespective of whether the activity is commercial, which
  withdraws the non-commercial framing for that item.

  **The scope of that open-ended tail cuts both ways and must be stated both
  ways.** It modifies the MEANS of emulating or redirecting COGNOSPHERE Services.
  It is not an open-ended list of software categories. This project emulates
  nothing and redirects nothing; it makes ordinary HTTPS requests to a third
  party. Reading the tail more broadly than that would overstate it, and reading
  the item as purely about private servers would understate it.

### Where the documents and the project meet

The chain that has to be reasoned about is short, and each link is separately
verifiable:

1. Section 7(c) prohibits scraping the COGNOSPHERE Services without permission.
2. This project does not fetch from any COGNOSPHERE Service. Its entire outbound
   surface is `https://enka.network`.
3. enka.network is a third party, and it is where collection from the publisher
   happens, if it happens.
4. This project displays publisher-derived player data obtained from that third
   party.
5. Section 3's assist-a-third-party tail exists, but closes Section 3's own list.

Whether that chain amounts to a problem is a question of contract construction
and of risk appetite. **This ADR does not resolve it and is not competent to.**
Nothing here is legal advice. What is recorded is what the documents say, what
the project does, and the fact that step 3 is the joint any assessment turns on.
That judgement is the operator's to make. An ADR that pretended to settle it
would be worse than one that names it, because settling it on this evidence would
retire the question without answering it.

## Decision

**Publish, and rest the posture on what this project verifiably is and is not -
zero vendored assets, zero vendored game data, no contact with the game client,
and a single third-party outbound host - rather than on any permission granted by
a fan-content FAQ.** The retrieved documents are context, not authorization. The
Legal FAQ is demoted from load-bearing to corroborating: its most-quoted sentence
answers a question about images, text and audiovisual materials, a category this
project is not in, and a non-prohibition of one thing is not evidence about
another.

**Being outside the scope of the published permissions is not the same as being
permitted.** That framing was right in the first version and survives the
correction unchanged. It never needed the FAQ, and it is stronger without it.

## How this ADR was wrong, and what that is worth

The first version of this document was drafted, refuted and rewritten inside a
single session. It was wrong in three checkable ways and confident in all three.

**1. Its headline claim was false, and it was the claim it was proudest of.** It
reported a literal-word probe of the Terms of Service returning NO for every one
of: robot, spider, scrape, scraper, crawl, data mining, API, companion. It used
that to overturn a summariser that had reported a scraping prohibition, then
generalised the win into doctrine. The prohibition is real and sits in Section
7(c). The summariser was right.

How the probe failed is the useful part, because it probably did run. On the
retrieved bytes, `\bscrape\b` matches zero times and `\bscraping\b` matches zero
times, while `\bscraped\b` matches twice. The drafter used the past participle. A
probe matching the dictionary form returns an honest, literal, reproducible NO
and still misses the clause. **A literal probe is only as good as its
morphology.** Search the stem, not the lemma.

The doctrine the first version reached for - that a summarised retrieval is not a
retrieval - is still sound, and this document practises it. But this ADR is not
entitled to cite this episode as evidence for it, because here the summary was
right and the literal probe was wrong. The lesson that actually earned itself is
the mirror image: **a probe returning a convenient negative deserves exactly the
scrutiny of a summary returning a convenient positive.**

**2. It searched for vocabulary the document does not use.** Measured on the
retrieved Legal FAQ body, case-insensitive:

```
website  8    program  6    service  12    app  6    non-commercial  3
tool     0    tracker  0    calculator 0   database 0   API 0   software 0
```

Reading those zeroes as reassurance was a category error: absence of your
vocabulary is not absence of the concept. The document's own words are program
and service. The same body frames its lists as non-exhaustive:

```
including but not limited to  3      such as  4      any other  4
and other  3                         current or future  1
```

The first version treated an open-ended enumeration as a closed one. It also
asserted that the word website appears exactly once in that body. It appears
eight times. That claim is removed rather than corrected, because it was never
doing any work.

**3. It admitted a gap for a reason that was not true.** It recorded that three
linked PDFs could not be read because no PDF renderer was available on the
machine. A renderer is available: `pdftotext` version 4.00 is on PATH. The real
gap is worse, and is recorded under re-open triggers below.

None of this was caught by a test, and none of it could have been.
`tests/test_docs_consistency.py` says in its own docstring that it deliberately
does not check prose accuracy. It was caught because something was pointed at the
document with instructions to refute it. That is the case for the adversarial
pass made concrete: three false claims in one short governing document, every one
checkable in minutes, none of them checked by the author.

## Consequences

- The posture no longer depends on a forum post. If the Legal FAQ is edited,
  moved or deleted, this decision does not move.
- The properties the decision rests on are testable, and some are already tested.
  `tests/test_licence_posture.py` guards the no-bulk-data and no-forbidden-dep
  arms inherited from ADR-002.
- A named, unresolved question now sits in the record in place of an unexamined
  assumption. It is the operator's to weigh, and it is written down so that
  weighing it does not require re-deriving it.
- Any future change that adds a vendored asset, a bulk data import, a COGNOSPHERE
  endpoint, or any read of the game client removes a load-bearing leg of this
  decision and requires re-opening it.

## Re-open triggers

- **The PDF hole.** Three documents linked from the terms page were not read this
  session. The reason given in the first version, that no renderer was available,
  was false. The true reason is that their URLs were never recorded anywhere in
  the tree, so the gap cannot be reproduced without re-visiting the page. Close
  it by recording the URLs and then reading them.
- **Any change to Terms of Service Section 7**, and in particular to the list of
  prohibited acts in clause c that contains scraped.
- **Any change to enka.network's own terms or its collection posture**, since
  step 3 of the chain above is the joint everything turns on.
- **Any change to this project's outbound host list**, currently one entry, and
  the cheapest thing here to re-measure.

## Rejected alternatives

- **Rest the posture on the Legal FAQ's non-prohibition of non-commercial
  personal use.** Rejected: it answers a question about images, text and
  audiovisual materials, none of which this project carries, and it arrives with
  three reservations including an express reservation of rights over derivative
  works. It was never load-bearing; it only looked load-bearing.
- **Treat the absence of the words tool, API and software from the FAQ as
  permission.** Rejected: the document uses program and service instead, and
  frames its lists as non-exhaustive.
- **Resolve the Section 7(c) question in this document.** Rejected: it is a
  contract-construction question, no agent working on this repository is
  competent to answer it, and an ADR is not the place. Naming it precisely is the
  useful act.
- **Drop the Legal FAQ entirely.** Rejected, narrowly. Questions 7 and 8 carry
  reserved rights a maintainer should know about, in particular the reserved
  right to refuse third-party platforms hosting programs for any reason at any
  time. Demoted to corroborating rather than removed.
