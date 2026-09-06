"""ResinCompute application test suite.

Run as `python -m pytest tests` from the repo root. The engine keeps its own
separate suite under `agents/pity_engine/tests`; never `pytest .` from the root,
per pytest.ini.

This file exists so the suite is a package and two slices cannot collide on a
bare module name (`test_core_ledger.py` and a future engine-side file of the
same name would otherwise be an import-file-mismatch waiting to happen). The
repo root reaches sys.path via the rootdir conftest.py.
"""
