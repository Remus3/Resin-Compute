# MERGE_TODO - CRLF writer sibling sweep

Branch: `worktree-agent-a2a04562af0e10df0`, based on `e1b20e6`.

## Files changed

| Path | Change |
|---|---|
| `ingest/enka_client.py` | `newline="\n"` on the cache envelope write |
| `ops/health.py` | `newline="\n"` on the fallback health write |
| `ops/supervisor.py` | `newline="\n"` on the runtime write probe |
| `scripts/bootstrap_data.py` | `newline="\n"` on `_fallback_atomic_write` |
| `tools/wish_authkey.py` | `newline="\n"` on `_atomic_write_text` |
| `tests/test_no_crlf_writers.py` | NEW - the guard, 7 tests |

## Files on the write-list that needed NO change

`tools/capture_supervisor.py` and `tools/first_run_capture.py` already pass
`newline="\n"`. In both the keyword sits on the CONTINUATION line of a wrapped
call, so the enumerating `git grep -n "write_text(" | grep -v newline=` reported
them as offenders. They are false positives. The new guard parses with `ast`
rather than scanning lines and spares both; `test_checker_reads_calls_not_lines`
is the regression arm for that.

## Needs the merger - NOT actionable from inside a worktree

An already-corrupted artefact exists on disk OUTSIDE the repository:
`captured_url.json` under the first-run capture root. 1945 bytes, 5 CRLF pairs,
0 lone LF, written by the now-fixed `tools/wish_authkey.py` capture path. It is
outside the worktree, so it was reported rather than edited. Backfill is a
CRLF-to-LF rewrite of that one file.

No tracked file needed a backfill: `ops/runtime/health.json` and
`data/bootstrap/account_snapshot.json` were both ABSENT at the time of measure.

## Note on the base

This worktree was created at `353e3c1`, which PREDATES the `core/atomic_io.py`
fix. It was rebased onto the declared fork point `e1b20e6` before any work, so
the guard runs against a tree where the origin defect is already fixed. Without
that rebase the guard would have flagged `core/atomic_io.py:69`, a file this
slice may not write.
