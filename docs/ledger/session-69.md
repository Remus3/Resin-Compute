# Session 69

Maint-KitRollout: FLEET-KIT v17 adoption.

## 2026-10-12 - /done gate, push, CI

- /done gate 2026-10-12 at 6f61e0d (working tree clean), Python 3.14 (host
  figures; CI is 3.11): licence 52 passed; docs 46 passed; qa 16 passed 0
  failed 2 skipped 4 noted; ruff clean; tests 4385 passed 6 skipped (204.65
  s); pity_engine 191 passed; node 110 pass 0 fail; dry run 0 pass 0 fail 7
  skip; mypy 43 files clean (advisory); kit check `17 []`. Whole suites ran
  through `ops/fleet_kit/fleet_suite_gate.py` with the absolute interpreter
  path and the claims-hook owner id typed literally.
- core.hooksPath read back `.githooks` at /done start.
- CI at 6f61e0d (gh run list): ci 38228507163 success, codeql 38228507246
  success. The push (0bff778..6f61e0d) was made during the session, before
  /done; origin/main read back 6f61e0d.

## 2026-10-12 - FLEET-KIT v17 (GITLOCK-SWEEP) vendored

- Commit 6f61e0d: `ops/fleet_kit/` vendored at v17, kit pin test repinned,
  ruff B007 per-file ignore for `ops/fleet_kit/fleet_claims.py` (never patch
  kit bytes). Verification: the kit check prints `17 []` (read back at
  /done); `tests/test_fleet_kit.py` in the 4385-passed app suite.
- ANSWER to MAIN (one note, kit v17 adopted at 6f61e0d, OK v17 expected)
  written to the MAIN-bound outbox and delivered, recipient copy
  hash-verified at the time of sending.
- Owner id trap: an invented owner id (kit-rollout.RSC) was refused by the
  claims hook; the session-id owner the hook prints is the accepted form.
- Decision: the ruff B007 ignore follows the existing per-file kit-ignore
  rule (ruff.toml); reversed when a kit version ships B007 clean.
