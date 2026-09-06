"""ResinCompute core package.

Deliberately empty of imports. `core.types` is the shared type contract and is
read-only to build slices; every other module here is a leaf utility that other
packages import by name (`from core.resin import resin_at`). Re-exporting them
from this file would create an import cycle the moment two core modules import
each other, so this file stays a docstring.

Dependency direction inside `core/`, which is acyclic by construction:

    config      -> stdlib only
    log_setup   -> config
    atomic_io   -> log_setup
    ledger      -> types, log_setup, resin
    resin       -> log_setup
    domains     -> log_setup
"""
