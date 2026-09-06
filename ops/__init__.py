"""ResinCompute operations lane.

Holds the supervision + health surface, mirroring Riot Commander's `ops/`:

  - `ops.health`     the `ops/runtime/health.json` contract (atomic writes).
  - `ops.supervisor` the watchdog that owns the managed child's lifecycle.

Nothing in this package imports a UI. It is the headless control plane and
must stay importable on a machine with no display and no browser.
"""
from __future__ import annotations

__all__ = ["health", "supervisor"]
