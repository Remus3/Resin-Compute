"""ResinCompute headless lane.

The non-interactive execution surface. Everything here runs with no UI, no
display and no user present, which is what makes it the lane a scheduled task
or a CI smoke test can drive:

  - `headless.jobs`   the ordered job registry.
  - `headless.runner` the CLI / daemon entrypoint that executes the registry.

The CI smoke test is exactly:

    python -m headless.runner --once --dry-run

That command must exit 0 with no network access and with every sibling slice
absent, so nothing in this package may import a sibling package at module
scope. Optional dependencies are imported lazily, inside the job body that
needs them, so a missing slice degrades ONE job to SKIP rather than breaking
import of the whole runner.
"""
from __future__ import annotations

__all__ = ["jobs", "runner"]
