# MERGE_TODO - slice P0

## Files changed by this slice

```
core/atomic_io.py
tests/test_core_atomic_io.py
```

Nothing else was edited. `MERGE_TODO.md` is this hand-off note, written on the
dispatching orchestrator's instruction; drop it at merge if unwanted.

## What changed

- `core/atomic_io.py` - new module constant `_NEWLINE = "\n"`, passed as
  `newline=_NEWLINE` on the temp write in `atomic_write_text`. No behaviour
  change other than the newline translation being disabled. `atomic_write_json`
  inherits it, since it funnels through `atomic_write_text`.
- `tests/test_core_atomic_io.py` - eight new tests, all asserting on RAW BYTES.
  Four of them were RED before the fix.

## For the merger - siblings NOT fixed, and why

Root cause is `Path.write_text` defaulting to `newline=None`. Nine other call
sites in this tree carry the identical property. All are OFF the P0 write-list
and were left untouched rather than swept in:

| Site | Target | Tracked? |
|---|---|---|
| `ops/health.py:153` | `ops/runtime/health.json` | gitignored (`ops/runtime/*`) |
| `scripts/bootstrap_data.py:74` | `data/bootstrap/account_snapshot.json` | **NOT gitignored - tracked-eligible** |
| `tools/wish_authkey.py:504` | authkey log and json target | check at merge |
| `ingest/enka_client.py:385` | `data/cache/enka/...` | gitignored (`data/cache/`) |
| `ops/supervisor.py:148` | probe file, no newline in payload | gitignored |
| `tools/capture_supervisor.py:220` | capture store outside the tree | untracked |
| `tools/first_run_capture.py:345` | capture store outside the tree | untracked |

`scripts/bootstrap_data.py` is the one worth a follow-up slice. It resolves
`atomic_write_text` BY NAME and prefers it, so its normal path now inherits this
fix - but its `_fallback_atomic_write` at line 74 still translates, and its
default output `data/bootstrap/account_snapshot.json` sits under `data/`, which
`.gitignore` does not exclude. `tests/test_line_endings.py` would fail on that
file if the fallback path were ever taken and the result committed.

## For the merger - an existing on-disk artefact is CRLF today

`ops/runtime/inbox_seen.json` in the MAIN checkout, measured this run:

```
bytes 14896
crlf_pairs 98
lone_lf 0
```

It is gitignored (`ops/runtime/*`), so it cannot turn the suite red. Its next
write through `scripts/watch_inbox.py:333` -> `atomic_write_json` now emits LF,
so it self-heals on the next `--mark`. No backfill was performed: the file is
outside this slice's write-list and outside the worktree.

`ops/runtime/health.json` does not exist on disk at all right now, so there is
nothing to backfill there.

## Declined: `atomic_write_bytes`

Not added. Reasons in the slice report; summary: zero consumers exist today, the
`newline` fix already gives byte-exact transport for every current and future
caller, and `SPEC_provenance.md` section 11 flags the choice as the
adjudicator's to rule on rather than the producer's. If the adjudicator rules
for it, it is a small follow-up on the same two files.
