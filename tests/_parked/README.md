# tests/_parked - written, not yet runnable

A test file here is COMPLETE and DELIBERATELY NOT COLLECTED. The `.parked`
suffix keeps it out of pytest's `test_*.py` glob, so the suite stays green while
the work waits on something outside the repository.

This is not a graveyard. A file here has a named blocker and a way to unpark it.
If a blocker is resolved and nobody unparks the file, delete it rather than
leaving it to rot - a stale parked test is worse than none, because it looks like
coverage that exists.

## test_engines_costs.py.parked

**Blocked on:** first-hand in-game observation of the seed-team cost table. See
`docs/GOAL_SPEC_SEED_TEAM.md` section 3.1, and ADR-002 for why a web-sourced
number cannot be used instead.

**What it is:** the failing-test half of the cost-table work, written TDD-first
before the session pivoted. It specifies a `engines/costs.py` that does not exist
yet: loading `data/costs/`, validating every material id against the verified
seed set, mapping costs onto the node ids `expand_character_goal` really emits,
reporting COVERAGE so an absent cost is a gap rather than a silent zero, and
composing the whole thing into a dated build plan.

**To unpark:** observe the costs, populate `data/costs/`, rename this file to
`tests/test_engines_costs.py`, run it, and implement `engines/costs.py` until it
is green. Expect the shipped-seed-data assertions to need updating to whatever
was actually observed - they currently assume only the one cost SPEC section 5
pins, Arlecchino ascension 2 taking two Fragment of a Golden Melody.
