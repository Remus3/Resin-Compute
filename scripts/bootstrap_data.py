"""Bootstrap the local data lane.

Two modes, one output shape:

    python scripts/bootstrap_data.py --offline            normalize local fixtures
    python scripts/bootstrap_data.py --uid 000000000      fetch one live profile

`--offline` is the DEFAULT. That is deliberate: the live path spends somebody's
rate limit against a service whose published policy forbids bulk collection, so
a bare invocation must never reach out on its own. `--dry-run` prints the plan
and writes nothing.

Nothing here vendors upstream data. The offline path normalizes the small
hand-authored fixtures in `data/fixtures/`, which exist for exactly this purpose.
See `data/fixtures/README.md` for the license findings.

ATOMIC WRITES
-------------
`core/atomic_io.py` is the sanctioned write path and is owned by a parallel
slice, so it may not exist in a partially-built tree. It is imported defensively
below with a local tmp-write-then-replace fallback that honours the same hard
rule, which keeps this script and its tests runnable standalone. The summary
line reports which writer was used, so a silent downgrade is impossible.

No raw traceback ever reaches stdout: every failure exits non-zero with a
friendly one-line message on stderr.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.types import EnkaMappedProfile  # noqa: E402
from ingest import static_data  # noqa: E402
from ingest.enka_client import EnkaClient, EnkaConfig, EnkaConfigError, EnkaUsageError  # noqa: E402
from ingest.enka_mapper import map_profile  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "data" / "bootstrap" / "account_snapshot.json"
SAMPLE_PROFILE = REPO_ROOT / "data" / "fixtures" / "enka_sample_profile.json"
SCHEMA_VERSION = 1

#: Writer contract: (path, text) -> None. Both the sanctioned module and the
#: local fallback are adapted to it.
Writer = Callable[[Path, str], None]


class BootstrapError(RuntimeError):
    """A failure that already carries a friendly, user-facing message."""


# ---------------------------------------------------------------------------
# Atomic write resolution
# ---------------------------------------------------------------------------


def _fallback_atomic_write(path: Path, text: str) -> None:
    """Local tmp-then-replace write.

    Same contract as the sanctioned module: never write a state file in place,
    because a reader can poll mid-write and see a truncated file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def resolve_writer() -> tuple[Writer, str]:
    """Prefer `core.atomic_io`, fall back locally when the slice is absent.

    Resolution is by NAME ONLY and touches no filesystem - a probe write would
    break the `--dry-run` promise that nothing is written. A signature mismatch
    is caught at the real call site instead, which then falls back.

    Only text-shaped entry points are considered. A json-shaped one takes an
    object rather than a string, so handing it text would produce a
    double-encoded file: a name miss falls back rather than guessing.
    """
    try:
        from core import atomic_io
    except ImportError:
        return _fallback_atomic_write, "local fallback (core.atomic_io not present)"

    for name in ("atomic_write_text", "write_text_atomic", "write_text", "atomic_write"):
        candidate = getattr(atomic_io, name, None)
        if not callable(candidate):
            continue

        def writer(path: Path, text: str, _fn: Callable[..., object] = candidate) -> None:
            _fn(path, text)

        return writer, f"core.atomic_io.{name}"

    return _fallback_atomic_write, "local fallback (no text writer found in core.atomic_io)"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _json_default(obj: object) -> object:
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"cannot serialize {type(obj).__name__}")


def _profile_to_dict(profile: EnkaMappedProfile) -> dict:
    if not is_dataclass(profile):
        raise BootstrapError("mapped profile is not a dataclass - refusing to serialize it")
    return asdict(profile)


def build_document(profile: EnkaMappedProfile, source: str, unknown_ids: list[int]) -> dict:
    """The normalized internal schema written to disk."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "source": source,
        "unknown_avatar_ids": sorted(unknown_ids),
        "seed_characters": [
            {"avatar_id": cid, "name": static_data.character_name(cid)} for cid in static_data.known_avatar_ids()
        ],
        "seed_materials": [
            {"material_id": mid, "name": static_data.material_name(mid)} for mid in static_data.known_material_ids()
        ],
        "profile": _profile_to_dict(profile),
    }


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def load_offline_payload(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BootstrapError(f"could not read the local fixture at {path}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BootstrapError(f"the local fixture at {path} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise BootstrapError(f"the local fixture at {path} is not a JSON object")
    return payload


def fetch_live_payload(uid: str, user_agent: str, cache_dir: Path) -> dict:
    config = EnkaConfig(user_agent=user_agent, cache_dir=cache_dir)
    client = EnkaClient(config=config)
    try:
        result = client.fetch_profile(uid)
    except EnkaConfigError as exc:
        raise BootstrapError(str(exc)) from exc
    except EnkaUsageError as exc:
        raise BootstrapError(str(exc)) from exc
    if not result.ok or result.profile_json is None:
        raise BootstrapError(result.friendly_message)
    return result.profile_json


def unknown_avatar_ids(profile: EnkaMappedProfile) -> list[int]:
    return [c.avatar_id for c in profile.characters if not static_data.is_known_character(c.avatar_id)]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bootstrap_data.py",
        description="Normalize local fixtures, or fetch one live profile, into the internal schema.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Normalize local fixtures instead of fetching. This is the default.",
    )
    parser.add_argument("--uid", default=None, help="Fetch this single UID live. Implies online mode.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan and write nothing.")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT), help="Output path for the normalized snapshot.")
    parser.add_argument("--fixture", default=str(SAMPLE_PROFILE), help="Offline source payload.")
    parser.add_argument(
        "--user-agent",
        default="",
        help="Custom User-Agent, REQUIRED by upstream policy for any live fetch.",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(REPO_ROOT / "data" / "cache" / "enka"),
        help="Where ttl-honouring cached responses are stored.",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.uid and args.offline:
        raise BootstrapError("--offline and --uid are mutually exclusive - pick one mode")

    out_path = Path(args.out)
    mode_online = bool(args.uid)

    if mode_online:
        payload = fetch_live_payload(str(args.uid), args.user_agent, Path(args.cache_dir))
        source = f"live:{args.uid}"
    else:
        fixture = Path(args.fixture)
        payload = load_offline_payload(fixture)
        source = f"offline:{fixture.name}"

    identity = static_data.StaticIdentity()
    profile = map_profile(payload, identity=identity, fetched_at=datetime.now(UTC))
    unknown = unknown_avatar_ids(profile)
    document = build_document(profile, source, unknown)

    entities = len(document["seed_characters"]) + len(document["seed_materials"])
    writer, writer_name = resolve_writer()

    print("bootstrap summary")
    print(f"  mode              : {'live' if mode_online else 'offline'}")
    print(f"  source            : {source}")
    print(f"  seed entities     : {entities} ({len(document['seed_characters'])} characters, "
          f"{len(document['seed_materials'])} materials)")
    print(f"  characters mapped : {len(profile.characters)}")
    print(f"  showcase open     : {profile.showcase_open}")
    print(f"  unknown avatar ids: {len(unknown)}" + (f" {sorted(unknown)}" if unknown else ""))
    print(f"  writer            : {writer_name}")
    print(f"  output            : {out_path}")

    if args.dry_run:
        print("  action            : DRY RUN - nothing written")
        return 0

    text = json.dumps(document, indent=2, sort_keys=True, default=_json_default)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        writer(out_path, text)
    except TypeError:
        # The resolved entry point did not take (path, text). Fall back rather
        # than fail: an atomic write is still an atomic write.
        _fallback_atomic_write(out_path, text)
        writer_name = "local fallback (signature mismatch in core.atomic_io)"
    except OSError as exc:
        raise BootstrapError(f"could not write the snapshot to {out_path}") from exc
    print(f"  action            : wrote {len(text)} bytes via {writer_name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point. Converts every failure into a friendly non-zero exit."""
    try:
        return run(argv)
    except BootstrapError as exc:
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("bootstrap cancelled", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI boundary: never print a raw traceback
        # The exception TYPE is safe to name and is enough to triage with. The
        # message may quote a payload or a URL, so it is deliberately dropped.
        print(f"bootstrap failed: unexpected {type(exc).__name__} - see the logs for detail", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
