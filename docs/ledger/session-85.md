# Session 85

## 2026-11-01 - MAIN FIX 1508: CI red on 95358dd, D1 closed stdout (headless run)

- CI red: b8813e8 moved `tests/test_uigf_cli.py` to a relative tolerance; this
  session tightened `FLOAT_REL` to 1e-15. Measured: a `round(..., 12)` mutant at
  `ingest/uigf.py` line 648 passes at 1e-14 and fails at 1e-15, tree restored with
  pycache purged on both sides. The remaining exact comparisons of computed
  floats in that file go through `_close`. The tolerance arm now pins the width.
- The README figure stays the one pin: the arm reads it from `README.md`, and the
  3.14 engine answer equals it while 3.11 is 1 ULP away (33.8216135353807, read
  with py -3.11).
- D1 HIGH closed by 7da57ca. Its arm undid its monkeypatch after capsys closed the
  stream, so `pytest -s` died with ValueError; it now uses `monkeypatch.context`,
  and `pytest tests/test_uigf_cli.py -s -k missing_stdout` read back exit 0.
- Focused figures 2026-11-01: `tests/test_uigf_cli.py` 147 passed on Python 3.14
  and on py -3.11 (PYTHONPATH to the 3.14 site-packages); ruff and mypy clean.
- D7 to D10 filed in `ROADMAP.md` "Adversary, RSC-1 CLI", each re-probed on the
  Windows host. The determinism row extended to both docstring copies.
