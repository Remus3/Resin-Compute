# Session 65

## 2026-10-09 - FLEET-KIT v14 adopted, MAIN FIX TEMP-1 landed

- Kit v14 (MAIN 0930 ORDER): slice A 546647f, merge e47af71. Vendored
  bytes under `ops/fleet_kit/` with `ops/fleet_kit/MANIFEST.json`; `tests/conftest.py`
  pins FLEET_SIDECAR_ROOT; `tests/test_fleet_kit.py` pins version 14. Kit
  check read back at the merged tree: `14 []`.
- MAIN FIX TEMP-1: slice B a9de110, merge afdd733. `pytest.ini` sets
  tmp_path_retention_count = 1; temp-policy and temp-hygiene tests updated;
  ROADMAP and the CLAUDE.md Testing section say never put a --basetemp
  inside the session scratchpad. Acceptance read-back (max basetemp dirs
  per scratchpad <= 1, max scratchpad entry count) is owed after a day of
  normal work, then an answer to MAIN; carried in `RSC-NEXT-SESSION.txt`.
- Identity section-4 survey (kit v14 `ops/fleet_kit/fleet_identity.py`): main 493
  commits; trigger ai-or-bot-author 2, ai-or-bot-committer 2; record 0;
  oldest violation depth 493 (the root). A history rewrite needs an
  operator or MAIN ORDER and runs only through `ops/fleet_kit/fleet_rewrite.py`; not
  started.
