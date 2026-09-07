# MERGE_TODO - inbox watcher digest-key test hardening

## Files changed in this slice

- `tests/test_watch_inbox.py` - the only file modified.

## Files on the write-list that were NOT changed

- `scripts/watch_inbox.py` - deliberately untouched. Every mutant that survived
  did so because the ARMS were weak, never because the module was wrong.
  `git diff -- scripts/watch_inbox.py` is empty. The module needs no fix.

## Merge seams

None. This slice adds test arms and one `import os` to a single test file. It
touches no shared contract, no `core/types.py`, no `core/atomic_io.py`.

Note for the merger: `scripts/watch_inbox.py` persists its watermark through
`core.atomic_io.atomic_write_json`. The parallel slice fixing CRLF in
`core/atomic_io.py` may change the bytes that watermark is written with. No arm
in this file asserts anything about the watermark's newlines, so the two slices
do not collide. `test_reporting_is_idempotent_and_does_not_even_touch_the_state_
file` compares the watermark's bytes to ITSELF across two reads, never to a
literal, so a newline change does not reach it.

## What was measured

Mutation testing against `tests/test_watch_inbox.py`, before and after.

| Mutant | Before | After |
|---|---|---|
| 1 - `_file_digest` returns `str(st_mtime_ns)` | KILLED (shape arms only) | KILLED (6 arms) |
| 1b - `_file_digest` returns `sha256(st_mtime_ns)` | KILLED (1 shape arm) | KILLED (5 arms) |
| 1c - note entry key is `sha256(st_mtime_ns)`, `_file_digest` intact | **SURVIVED GREEN** | KILLED |
| 2 - `_file_digest` returns `str(st_size)` | KILLED (shape arms only) | KILLED |
| 2b - `_file_digest` returns `sha256(st_size)` | KILLED (1 shape arm) | KILLED (5 arms) |
| 2c - drop manifest line carries `st_size` | **SURVIVED GREEN** | KILLED (2 arms) |
| 2d - drop manifest line carries `st_mtime_ns` | not measured before | KILLED (2 arms) |
| 3 - 16-character payload preview appended to the report | **SURVIVED GREEN** | KILLED (3 modes) |

Every mutation was reverted with `git checkout --` and the empty diff confirmed
before moving on.

## Arms added

- `_restore_mtime_provably` - pushes the mtime away, asserts it moved, restores,
  asserts exact equality. Without that push the restore could be a silent no-op
  and the control unarmed.
- `test_a_note_edited_at_constant_length_with_the_mtime_restored_re_surfaces`
- `test_a_drop_payload_edited_at_constant_length_and_mtime_re_surfaces_it`
- `test_the_drop_manifest_moves_when_only_the_bytes_move`
- `test_the_note_digest_moves_when_only_the_bytes_move`
- `_payload_window_sweep` returning `(checked, offenders)`
- `test_the_payload_window_sweep_actually_fires` - the non-vacuity arm
- `test_the_report_leaks_no_window_of_a_payload` - parametrized over 3 modes
