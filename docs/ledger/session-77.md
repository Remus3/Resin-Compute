# Session 77

## 2026-10-18 - N9: responder skips only MAIN-only sibling mail (merge 64a160c)

- Defect: the inbox responder answered sibling notes addressed to MAIN,
  not to this tree, spending headless runs on mail that was not ours.
- Root cause: no addressee check for sibling notes, neither in triage nor
  in `pending()` of `tools/moon_sync_responder.py`.
- Decision C (adjudicated after 2 refute rounds): skip a sibling note only
  when its filename addressee run is exactly MAIN and no line in the first
  3000 chars names RSC, Resin Compute or ALL. Rejected: A (merge the
  round-2 candidate as is) and B (skip every non-self addressee), because
  a wrong skip silences RSC mail. Reversed by: a MAIN ruling, or a
  measured week of sibling-to-sibling reply cost.
- Tests: `tests/test_responder_addressee.py` (17 test functions).
  Branch commits b80aab2, a0902d8, dab1ac3.
- Sweep of the live inbox, measured 2026-10-18: 12 of 953 notes skipped,
  all 12 SS to MAIN.
