"""Ingest lane: fetch an external profile, map it onto the internal contract.

Three modules, one responsibility each:

- `enka_client`   network boundary. Re-implemented from the published protocol,
                  stdlib only, custom User-Agent enforced, response `ttl`
                  honoured, no UID enumeration.
- `enka_mapper`   pure payload -> `core.types` mapping. Every verified upstream
                  trap is absorbed here so no consumer inherits one.
- `static_data`   the only place character and material identity lives, loaded
                  from small hand-authored fixtures.

NO upstream dataset is vendored anywhere in this package. See
`data/fixtures/README.md` for the license findings that decided that.
"""
from __future__ import annotations

from ingest.enka_client import (
    MAX_BATCH_UIDS,
    EnkaClient,
    EnkaConfig,
    EnkaConfigError,
    EnkaUsageError,
    FetchResult,
)
from ingest.enka_mapper import (
    fold_talent_levels,
    map_character,
    map_profile,
    refinement_from_affix_map,
)
from ingest.static_data import (
    StaticIdentity,
    character_name,
    material_name,
)

__all__ = [
    "MAX_BATCH_UIDS",
    "EnkaClient",
    "EnkaConfig",
    "EnkaConfigError",
    "EnkaUsageError",
    "FetchResult",
    "StaticIdentity",
    "character_name",
    "fold_talent_levels",
    "map_character",
    "map_profile",
    "material_name",
    "refinement_from_affix_map",
]
