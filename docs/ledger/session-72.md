# Session 72

## 2026-10-13 - merge 0w and 0y, 0y F1, 0z root cause

- 0w merged: attended sends route through `tools/send_note.py`
  (`.claude/commands/done.md`, `.claude/commands/orchestrated-run.md`;
  test `tests/test_send_path_guard.py`).
- 0y merged: ui-auditor routing defers to the ui-audit skip list
  (`.claude/agents/builder.md`, `.claude/agents/planner.md`; test
  `tests/test_builder_ui_audit_rule.py`). `tests/_markers.py` auto-merged
  with both slices' entries kept, sorted.
- 0y F1 (adjudicated Option A after 2 refute rounds): the section 7 merge
  check in `.claude/commands/orchestrated-run.md` now defers to "When to
  skip this entirely" in `.claude/commands/ui-audit.md`. The widened
  detector (ui-auditor, `/ui-audit`, `AUDIT: PASS`) first FAILED
  `test_every_ui_auditor_routing_defers_to_ui_audit_skip_list` naming
  orchestrated-run.md, then passed after the edit.
- 0z: core.hooksPath drift root-caused to Claude Code's own worktree setup
  (absolute `<main root>\.githooks` written to the shared `.git/config`).
  `.claude/commands/done.md` section 0 accepts either spelling; test
  `tests/test_done_hookspath_rule.py` (red on the old byte-equal bullet).
  Rejected: `extensions.worktreeConfig`.
- Seam: merging 0w and 0y took `tests/` to 135 tracked paths, equal to the
  floor; `test_the_floor_is_reachable_and_keeps_clearance_below_the_real_tree`
  FAILED. `_MIN_TRACKED_PATHS` raised 135 -> 155 in
  `tests/test_machine_identity.py` and `tests/test_licence_posture.py`.
