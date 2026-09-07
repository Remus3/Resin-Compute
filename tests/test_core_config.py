"""Guards for core.config, and for the cross-repo lane ceiling in particular.

Most of what follows is a plain field-and-default check. One arm is not:
`test_no_single_env_var_can_raise_the_lane_ceiling` guards a DESIGN DECISION
rather than a behaviour, and it is the reason this file exists at all.

MAX_CONCURRENT_LANES is a ceiling on total concurrent executor calls SHARED
with two sibling repositories on this machine - Legion Wallpaper and Riot
Commander - which admit work against one lockfile slot bucket. Each repository
reads its OWN copy of the number. The bucket therefore bounds nothing unless
all three copies agree, and an environment override on any single participant
raises the EFFECTIVE ceiling for all three, because each side admits holders
against its own reading. That is why this one value is deliberately not
env-derived while every other field in the module is, and why a future commit
that helpfully wires it to os.environ has to turn this file red.

NON-VACUITY. A test that sets an environment variable and then asserts nothing
changed passes just as happily when the variable never reached the code at all.
`test_env_vars_do_reach_load_config` is the paired arm: it moves a field that
IS env-derived through the same monkeypatch mechanism in the same process, so
every "still 3" assertion here is known to be measuring something.

The enumerated names are a guess and can only catch names someone thought of.
`test_load_config_never_names_the_ceiling_field` is the arm that is not a
guess: it reads `load_config` itself and fails on any wiring, under any name,
from any source.
"""
from __future__ import annotations

import dataclasses
import inspect

import pytest

from core.config import DEFAULT_ENGINE_HOST, MAX_CONCURRENT_LANES, Config, load_config

# Written out independently rather than compared against the imported constant.
# `assert MAX_CONCURRENT_LANES == MAX_CONCURRENT_LANES` proves nothing, and a
# test that imports its own expectation is a test about no number at all.
CROSS_REPO_CEILING = 3

CONTRACT = (
    "MAX_CONCURRENT_LANES is a CROSS-REPO ceiling on total concurrent executor "
    "calls, shared with Riot Commander and Legion Wallpaper against ONE lockfile "
    "slot bucket at C:/ProgramData/lw-loop/slots. Each repository reads its own "
    "copy, so all three must declare the SAME number - if they disagree the "
    "governor silently admits max(a, b) holders and becomes theatre. Riot "
    "Commander and Legion Wallpaper both declare 3. Changing it is a joint act "
    "across all three repositories in one round, never a unilateral edit here."
)

# Names a future contributor might plausibly reach for while wiring this to the
# environment. Deliberately over-broad: the cost of an extra name is one fast
# assertion, and the cost of a missing one is a silently raised shared ceiling.
PLAUSIBLE_ENV_NAMES = (
    "RESIN_MAX_CONCURRENT_LANES",
    "MAX_CONCURRENT_LANES",
    "RC_MAX_CONCURRENT_LANES",
    "RESIN_MAX_LANES",
    "MAX_LANES",
    "RESIN_CONCURRENT_LANES",
    "LW_MAX_CONCURRENT_LANES",
    "LW_LOOP_MAX_CONCURRENT_LANES",
)


# --- the module constant --------------------------------------------------


def test_the_lane_ceiling_is_three():
    assert MAX_CONCURRENT_LANES == CROSS_REPO_CEILING, CONTRACT


def test_the_lane_ceiling_is_a_plain_int():
    # `isinstance(x, int)` would accept True, because bool subclasses int, and
    # a ceiling of True admits one holder. The type check is therefore exact.
    assert type(MAX_CONCURRENT_LANES) is int, CONTRACT


def test_the_module_docstring_still_carries_the_rationale():
    """The reasoning is load-bearing, so its deletion is a test failure.

    Someone who removes the note is very likely the same person about to wire
    the value to the environment, which is the failure this file exists to
    prevent. Matched on the constant name only - loose enough to survive an
    honest rewording, tight enough to catch a deletion.
    """
    import core.config as config_module

    doc = config_module.__doc__ or ""
    assert "MAX_CONCURRENT_LANES" in doc, (
        "core/config.py no longer explains why the lane ceiling is not an "
        "environment variable. " + CONTRACT
    )


# --- the dataclass field --------------------------------------------------


def test_a_default_constructed_config_carries_the_ceiling():
    assert Config().max_concurrent_lanes == CROSS_REPO_CEILING, CONTRACT


def test_load_config_carries_the_ceiling():
    assert load_config().max_concurrent_lanes == CROSS_REPO_CEILING, CONTRACT


def test_the_ceiling_is_the_last_field_on_the_dataclass():
    """Guards this tree's append-at-END dataclass convention.

    A new field inserted mid-class silently reassigns every positional
    construction of Config that already exists, so the convention is checked
    rather than trusted. If a later field is appended after this one, the
    correct fix is to move THAT field's assertion here, not to relax this.
    """
    names = [f.name for f in dataclasses.fields(Config)]
    assert names[-1] == "max_concurrent_lanes", (
        f"max_concurrent_lanes must be the LAST field on Config; field order is {names}"
    )


def test_the_ceiling_field_is_annotated_int():
    by_name = {f.name: f for f in dataclasses.fields(Config)}
    assert "max_concurrent_lanes" in by_name, (
        f"max_concurrent_lanes is not a dataclass FIELD of Config; fields are {sorted(by_name)}"
    )
    # `from __future__ import annotations` in core/config.py leaves the
    # annotation as the STRING "int"; both forms are accepted so the assertion
    # does not depend on that import staying put.
    assert by_name["max_concurrent_lanes"].type in ("int", int)


def test_the_config_dataclass_is_still_frozen():
    """Frozen is what stops one consumer raising the ceiling for another.

    A non-frozen Config would let any caller in the process mutate the shared
    number after load, which is the same failure as an env override with a
    smaller blast radius.
    """
    cfg = load_config()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.max_concurrent_lanes = 9


# --- the design decision: NOT environment-overridable ---------------------


@pytest.mark.parametrize("name", PLAUSIBLE_ENV_NAMES)
def test_no_single_env_var_can_raise_the_lane_ceiling(monkeypatch, name):
    monkeypatch.setenv(name, "9")
    assert load_config().max_concurrent_lanes == CROSS_REPO_CEILING, (
        f"{name}=9 moved the lane ceiling. A cross-repo ceiling one participant "
        "can raise alone is not a ceiling. " + CONTRACT
    )


def test_all_the_plausible_env_vars_at_once_still_cannot_raise_it(monkeypatch):
    for name in PLAUSIBLE_ENV_NAMES:
        monkeypatch.setenv(name, "9")
    assert load_config().max_concurrent_lanes == CROSS_REPO_CEILING, CONTRACT
    assert MAX_CONCURRENT_LANES == CROSS_REPO_CEILING, CONTRACT


def test_env_vars_do_reach_load_config(monkeypatch):
    """NON-VACUITY ARM for every "still 3" assertion above.

    If monkeypatch.setenv never reached load_config - a cached Config, a
    read-at-import default, a fixture that scrubs the environment - the
    override tests would pass while measuring nothing. This moves a field that
    IS env-derived through the identical mechanism and observes it move.
    """
    monkeypatch.delenv("RESIN_ENGINE_HOST", raising=False)
    before = load_config()
    assert before.engine_host == DEFAULT_ENGINE_HOST

    monkeypatch.setenv("RESIN_ENGINE_HOST", "10.0.0.7")
    after = load_config()
    assert after.engine_host == "10.0.0.7", (
        "setenv did not reach load_config, so the env-override guards above are vacuous"
    )
    assert after.engine_host != DEFAULT_ENGINE_HOST

    # Same process, same mechanism, same call - and the ceiling did not move.
    assert after.max_concurrent_lanes == CROSS_REPO_CEILING, CONTRACT


def test_load_config_never_names_the_ceiling_field():
    """The arm that is not a guess.

    A name list catches only the names someone thought of. This reads the body
    of `load_config` and asserts the field is never passed at all, so wiring it
    to os.environ under a name nobody enumerated still fails here.
    """
    source = inspect.getsource(load_config)
    assert "max_concurrent_lanes" not in source, (
        "load_config() now sets max_concurrent_lanes. It must stay at the "
        "dataclass default so no local environment can move it. " + CONTRACT
    )
