# data/costs

Empty on purpose. This directory holds first-hand cost tables and nothing else.

**This file exists so the directory does.** Git does not store empty
directories, so without a tracked file here `data/costs/` is present on the
machine that created it and absent in every fresh clone. That is not a
theoretical difference: `docs/GOAL_SPEC_SEED_TEAM.md` cites this path, and
`tests/test_docs_consistency.py` asserts that every backticked path in a
governing doc resolves. The guard passed locally and failed on the CI runner,
which is the first place a fresh clone actually got checked out.

## What goes here

Ascension, talent and weapon cost tables: Mora and material quantities per
threshold. `engines/objectives.py` is mechanism only and takes materials as a
caller-supplied argument; nothing supplies them yet. This directory is where
that supply lands.

## The contract on every row

**Every row carries a `source` field.** A number without a stated origin cannot
be audited later, and the whole reason this directory is empty is that no
audited origin exists yet.

- **First-hand in-game observation is the only currently acceptable source.**
  `docs/GOAL_SPEC_SEED_TEAM.md` section 3.1 is the gate. The account has not
  been played, so no such observation exists.
- **Web-sourced figures must NOT enter this directory.** The three that arrived
  from a web assistant are stamped unverified in the goal spec and are
  deliberately not here. `tests/test_goal_spec.py` fails if they are copied in.
- **A licensed bulk source is a separate decision** with the same gate as every
  other data source: `docs/LICENSE_NOTES.md` and ADR-002. Every upstream that
  publishes these tables wraps HoYoverse-copyright data, and a permissive
  licence on a wrapper grants rights only to that author's own compilation.
  ADR-006 dissolved the copyleft objection to two of them and nothing else.

## Where `source` now comes from

**It is DERIVED, and it is no longer a free string.** The row-scoped provenance
schema - `docs/PROVENANCE_SCHEMA.md`, implemented in `core/provenance.py` -
makes every row carry a tuple of receipts, and `render_source` renders the
`source` summary from that tuple. The two therefore cannot disagree, and a
hand-written `source` that contradicts the receipts is REFUSED rather than
reported.

A receipt names the artefact a number was read from, that artefact's sha256, and
HOW it was read. What that buys this directory specifically:

- **A number without an origin cannot enter at all.** A row with an empty
  provenance tuple is refused before any file is written.
- **"I saw it in two places" is now arithmetic.** Two reads of one screenshot
  are ONE witness, because both receipts name the same parent artefact. Two
  numbers merely consistent with each other were never two facts, and the
  count no longer depends on an author remembering that.
- **A retraction has somewhere to live.** Operator testimony is a recordable
  read method, so a number that was refuted stops counting as support instead
  of quietly staying in the table.

The first-hand-observation gate above is UNCHANGED. The schema describes how a
first-hand number carries its receipt; it does not widen what counts as one.

`tests/_parked/` holds the complete, TDD-first test file waiting for these
numbers, with its own README saying how to unpark it. Note for whoever unparks
it: it writes a single nested JSON document, and provenance rows are JSON Lines,
one row and one receipt set per line. Nothing has to migrate - no row exists -
but its loader arms will need revising.
