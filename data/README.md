# data - observations, and the receipt each one carries

Two different kinds of thing live under this directory and the difference
decides what the rules are.

- `data/fixtures/` is **hand-authored** material for tests and the offline
  bootstrap path. Nothing upstream is vendored there and nothing ever will be.
  Its own README says which of its files are verified public game fact typed in
  by hand and which one is invented.
- Everything else here is **observation**: values read off the game, out of a
  file the game wrote, or out of a response an endpoint gave. Those are the rows
  this README is about.

**No observation row exists yet.** That is a statement of fact rather than an
oversight - the schema had to exist before the first row landed, so that the
first row could not set a worse precedent than the second one would have to
follow.

## Every observation row carries a receipt

The contract is `docs/PROVENANCE_SCHEMA.md`, implemented in
`core/provenance.py` and held by `tests/test_provenance.py`. A row names the
artefact it was read from, that artefact's sha256, and HOW it was read. A row
with no receipt is REFUSED - not warned about.

The short form of the rules a stranger most often trips over:

1. **A negative needs a sampling rate.** "Not found" is a claim about a SEARCH.
   A search with no stated rate is unreportable, so a `not_found` row with no
   sampling reference is refused. Not found at 1 fps over a 15 fps recording is
   not not present.
2. **A measured zero is not a not-found.** A surface that answered, and answered
   none, is a different claim from a sweep that found nothing.
3. **Two reads of one artefact are one witness.** The count is arithmetic: a
   receipt names the parent artefact it came out of, so two pixel reads of one
   crop collapse. Pixels and bytes agreeing is corroboration; two pixel reads
   agreeing is not.
4. **A derived value names its inputs.** A derivation that names none is an
   assertion wearing a receipt.

## Shape

One row per line, JSON Lines, in a per-table directory. Written only through
`core/atomic_io.py`, whole file at a time - never appended in place, because a
reader polling mid-append sees a torn last line.

## What must never enter this directory

- **Account values of any kind.** No uid, nickname, region, authkey, account id,
  token or session key, in a payload key, a payload value or a locator. The
  validator refuses all of them by name. The capture store lives outside the
  tree deliberately, and locators are relative to a capture root named there.
- **Absolute paths.** A locator naming a drive names one machine.
- **Web-sourced or unsourced figures.** `docs/GOAL_SPEC_SEED_TEAM.md` section
  3.1 is the gate and it is unchanged: first-hand observation is the only
  currently acceptable source for a cost number. `tests/test_goal_spec.py` fails
  if the unverified figures are copied in.
- **Vendored datasets.** `docs/LICENSE_NOTES.md` and the data-posture ADR decide
  that, and this schema does not relax it. `tests/test_licence_posture.py` fails
  any file here over 64 KiB, on the reasoning that a bulk dump does not arrive
  announced - it arrives as a big file.
