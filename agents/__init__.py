"""Local compute engines for ResinCompute.

One package per engine, mirroring Riot Commander's ``agents/`` layout where
Daemon Slayer lives beside its own tests and CHANGELOG. An engine here is pure,
deterministic and versioned, and is exposed over a local HTTP port rather than
being imported across slice boundaries.
"""
