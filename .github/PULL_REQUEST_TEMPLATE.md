# What this changes

<!-- One or two sentences. What is different after this lands, and why. -->

## Why

<!-- The problem, not the patch. Link an issue or an ADR if there is one. -->

## How it was verified

Paste the command AND the result you observed on THIS branch. Please do not
restate a suite count as a claim about the project - counts are not guarded and
go stale - but do say what the run reported for the run you actually made.

```
python -m pytest tests
python -m pytest agents/pity_engine
python -m ruff check .
python -m mypy
```

<!-- Results here. Include exit codes or the summary line, not "all green". -->

## Checklist

- [ ] The hooks are installed in my clone (`python scripts/install_hooks.py`).
      A fresh clone runs none, so this is not automatic.
- [ ] Both suites were run SEPARATELY. I did not run `pytest .` from the root.
- [ ] `python -m ruff check .` is clean.
- [ ] `python -m mypy` was run. I am not citing its success as evidence about
      code outside the `files=` roots in `mypy.ini`.
- [ ] Every authored byte is seven-bit ASCII: no em-dashes, no en-dashes, no
      smart quotes, in code, comments, docs or the commit message.
- [ ] New behaviour has a test, and that test failed before the change for the
      right reason.
- [ ] A bug fix also fixes the sibling cases sharing the same root cause, and
      backfills any records the bug already corrupted.
- [ ] Any new guard has a non-vacuity arm proving the detector actually fires.
- [ ] **No game data is vendored.** Nothing was added to `data/` that did not
      come from first-hand observation or from hand-authored public fact.
- [ ] Any new dependency, dataset or ingest target carries a licence verdict
      checked against `docs/LICENSE_NOTES.md`.
- [ ] State written for another process to read goes through `core/atomic_io.py`.
- [ ] No raw API or error string reaches a user-facing surface.
- [ ] Commit subjects match Conventional Commits, and carry no agent trailers.
- [ ] Documents I touched point only at paths that exist and that git stores.
- [ ] I have read `CONTRIBUTING.md`, and my contribution is offered under
      GPL-3.0-or-later.

## Anything you could not verify

<!-- State it as unverified rather than rounding an uncertainty up to a claim.
     An honest gap here is worth more than a confident checkbox. -->
