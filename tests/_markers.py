"""The central registry for the `plumbing` and `reads_docs` markers.

Applied to every collected item by `pytest_collection_modifyitems` in
`tests/conftest.py`; no test module carries these as decorators, so a module
is reclassified here, in one place. Guarded by `tests/test_test_markers.py`.
Read by `scripts/prepush_select.py`, which is why this file holds data only and
imports nothing from pytest.

Paths are repo-relative and POSIX-spelled, exactly as `git ls-files` prints
them. A module listed nowhere is PRODUCT: it runs on every CI push and is
eligible for every pre-push selection. That is the safe default, so a new
module needs no entry here unless it is plumbing or reads docs.

PLUMBING - the module's SUBJECT lives under a plumbing root: tools/,
headless/, scripts/, ops/, .githooks/, .github/ or .claude/ (the fleet kit,
the responder, the hooks, the CI workflows, the headless runner, the inbox
watcher). CI push runs and the pre-push hook run these only when such a root
changes; the nightly schedule always runs them. Deliberately NOT plumbing even
though a tool implements them: the tree-wide sweeps (line endings, secret
literals, sibling names, machine identity, interpreter pinning, the git
subprocess census), because a product edit can violate those; the headless
JOBS that drive core/ (jobs, persist_state, reconcile_ledger); and every
conftest, pytest.ini and mypy-scope meta-test, whose subjects force a FULL run.

READS_DOCS - the module reads tracked .md content: a named document, or a
sweep over every tracked file that includes the docs. The docs-guards workflow
runs exactly these on a docs-only push. DOCS_GREP_EXEMPT lists the modules
the old docs-lane grep selected that only MENTION markdown in prose or build
throwaway .md fixtures under tmp_path; `tests/test_test_markers.py` fails on
any grep hit that is in neither list.
"""
from __future__ import annotations

PLUMBING_ROOTS: tuple[str, ...] = (
    "tools/",
    "headless/",
    "scripts/",
    "ops/",
    ".githooks/",
    ".github/",
    ".claude/",
)

PLUMBING: frozenset[str] = frozenset(
    {
        "tests/test_agent_roster.py",
        "tests/test_carrier_population_prose.py",
        "tests/test_ci_history_depth.py",
        "tests/test_ci_workflow_complement.py",
        "tests/test_commit_trailers.py",
        "tests/test_corpus_statement.py",
        "tests/test_dev_pin_declaration.py",
        "tests/test_docs_hook_commands.py",
        "tests/test_first_run_capture_walk.py",
        "tests/test_fleet_kit.py",
        "tests/test_fleet_kit_v9_adoption.py",
        "tests/test_fleet_kit_v10_adoption.py",
        "tests/test_fleet_kit_v12_adoption.py",
        "tests/test_fleet_kit_v13_adoption.py",
        "tests/test_fleet_lanes_adoption.py",
        "tests/test_gate_mutation_runner.py",
        "tests/test_gate_name_bindings.py",
        "tests/test_headless_env.py",
        "tests/test_headless_runner.py",
        "tests/test_headless_runner_checklist.py",
        "tests/test_headless_runner_halt.py",
        "tests/test_headless_runner_lock_budget.py",
        "tests/test_headless_runner_orphan_temps.py",
        "tests/test_headless_runner_quarantine.py",
        "tests/test_headless_runner_slots.py",
        "tests/test_hook_gate.py",
        "tests/test_hook_interpreter.py",
        "tests/test_install_hooks_resolution.py",
        "tests/test_loop_concurrency.py",
        "tests/test_moon_sync_responder.py",
        "tests/test_ops_health.py",
        "tests/test_precommit_gate_corpus.py",
        "tests/test_precommit_gate_message.py",
        "tests/test_prepush_select.py",
        "tests/test_prepush_skip_reporting.py",
        "tests/test_responder_audience.py",
        "tests/test_responder_broadcast_refusal.py",
        "tests/test_responder_checklist.py",
        "tests/test_responder_degraded_write.py",
        "tests/test_responder_delivery_gates.py",
        "tests/test_responder_gate_census.py",
        "tests/test_responder_inbox_v8.py",
        "tests/test_responder_invocation_trim.py",
        "tests/test_responder_loop_breakers.py",
        "tests/test_responder_main_provenance.py",
        "tests/test_responder_no_console_window.py",
        "tests/test_responder_refusal_gates.py",
        "tests/test_responder_refusal_gates_fire.py",
        "tests/test_responder_spawn_census.py",
        "tests/test_responder_spawn_cwd.py",
        "tests/test_responder_task_argv.py",
        "tests/test_responder_uniform_budget.py",
        "tests/test_roster_retired.py",
        "tests/test_session_checklist.py",
        "tests/test_session_hooks.py",
        "tests/test_stop_claim_gate.py",
        "tests/test_supervisor_task_argv.py",
        "tests/test_supply_chain.py",
        "tests/test_task_liveness.py",
        "tests/test_task_state_claims.py",
        "tests/test_watch_inbox.py",
        "tests/test_watch_inbox_log_discard.py",
        "tests/test_watch_inbox_session.py",
        "tests/test_watch_inbox_walk_pruning.py",
        "tests/test_write_tracer.py",
    }
)

READS_DOCS: frozenset[str] = frozenset(
    {
        "tests/test_agent_roster.py",
        "tests/test_carrier_population_prose.py",
        "tests/test_channel_doc_pin.py",
        "tests/test_ci_workflow_complement.py",
        "tests/test_docs_consistency.py",
        "tests/test_docs_hook_commands.py",
        "tests/test_fleet_kit.py",
        "tests/test_fleet_kit_v9_adoption.py",
        "tests/test_fleet_kit_v10_adoption.py",
        "tests/test_fleet_kit_v12_adoption.py",
        "tests/test_goal_spec.py",
        "tests/test_guard_worktree_exclusion.py",
        "tests/test_licence_posture.py",
        "tests/test_line_endings.py",
        "tests/test_machine_identity.py",
        "tests/test_no_secret_literals.py",
        "tests/test_no_sibling_names.py",
        "tests/test_precommit_gate_corpus.py",
        "tests/test_readme_tree.py",
        "tests/test_session_checklist.py",
        "tests/test_task_state_claims.py",
        "tests/test_vendored_provenance.py",
    }
)

DOCS_GREP_EXEMPT: frozenset[str] = frozenset(
    {
        "tests/test_commit_trailers.py",
        "tests/test_core_config.py",
        "tests/test_core_state_io.py",
        "tests/test_corpus_statement.py",
        "tests/test_dev_pin_declaration.py",
        "tests/test_empty_parametrize_policy.py",
        "tests/test_engines_artifact_score.py",
        "tests/test_fleet_lanes_adoption.py",
        "tests/test_git_subprocess_census.py",
        "tests/test_headless_env.py",
        "tests/test_headless_runner_checklist.py",
        "tests/test_hook_gate.py",
        "tests/test_hook_interpreter.py",
        "tests/test_ingest_client.py",
        "tests/test_ingest_mapper.py",
        "tests/test_live_runtime_fence.py",
        "tests/test_loop_concurrency.py",
        "tests/test_moon_sync_responder.py",
        "tests/test_mypy_scope.py",
        "tests/test_no_crlf_writers.py",
        "tests/test_prepush_select.py",
        "tests/test_provenance.py",
        "tests/test_publish_next_session.py",
        "tests/test_responder_audience.py",
        "tests/test_responder_broadcast_refusal.py",
        "tests/test_responder_checklist.py",
        "tests/test_responder_degraded_write.py",
        "tests/test_responder_delivery_gates.py",
        "tests/test_responder_gate_census.py",
        "tests/test_responder_inbox_v8.py",
        "tests/test_responder_loop_breakers.py",
        "tests/test_responder_main_provenance.py",
        "tests/test_responder_no_console_window.py",
        "tests/test_responder_refusal_gates.py",
        "tests/test_responder_refusal_gates_fire.py",
        "tests/test_responder_spawn_census.py",
        "tests/test_responder_spawn_cwd.py",
        "tests/test_responder_uniform_budget.py",
        "tests/test_session_hooks.py",
        "tests/test_shell_contract.py",
        "tests/test_stop_claim_gate.py",
        "tests/test_surface_plan_rotation.py",
        "tests/test_surface_teams.py",
        "tests/test_test_markers.py",
        "tests/test_watch_inbox.py",
        "tests/test_watch_inbox_log_discard.py",
        "tests/test_watch_inbox_session.py",
        "tests/test_watch_inbox_walk_pruning.py",
    }
)

#: SLOW - individual tests, by node id without any parametrize suffix, that
#: took 2 s or more in one phase of a measured `--durations` run of the whole
#: application suite (2026-10-09, this host, Python 3.14). `.githooks/pre-push`
#: deselects `slow`; CI and the schedule run them. The four gate-mutation arms
#: share two module-scoped campaign fixtures (about 10 s and 2 s of setup), so
#: they are marked together - marking one would only move the setup cost onto
#: the next. Re-measure with `--durations=25`, which CI now prints into the job
#: summary, before adding or removing an entry.
SLOW: frozenset[str] = frozenset(
    {
        "tests/test_gate_mutation_runner.py::test_the_former_hash_line_survivors_are_killed_in_the_main_table",
        "tests/test_gate_mutation_runner.py::test_every_message_mutant_is_killed_by_the_real_gate",
        "tests/test_gate_mutation_runner.py::test_non_vacuity_a_clean_message_lands_through_the_armed_gate",
        "tests/test_gate_mutation_runner.py::test_non_vacuity_a_disarmed_clone_lets_every_mutant_survive",
        "tests/test_responder_checklist.py::test_a_reader_held_past_the_retry_leaves_no_orphaned_tmp",
        "tests/test_gate_name_bindings.py::test_no_proper_prefix_or_suffix_of_an_anchor_can_restore_a_match",
        "tests/test_session_hooks.py::test_this_file_stamps_nothing_into_the_live_runtime_records",
        "tests/test_headless_runner_checklist.py::test_a_failing_progress_write_never_fails_a_pass",
        "tests/test_git_subprocess_census.py::test_the_agreement_arm_goes_red_under_a_narrowed_resolver",
        "tests/test_headless_env.py::test_a_closed_port_is_refused_by_a_real_dial",
    }
)
