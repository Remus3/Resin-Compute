"""Repo-root pytest hooks - apply to BOTH suites.

`tests/conftest.py` only reaches `tests/`. The engine suite under
`agents/pity_engine/tests/` needs the same repo root on `sys.path` to import
`core.types`, and a rootdir conftest is the only place one installation covers
both. This mirrors Riot Commander's root conftest for the same reason.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
