"""Tests for the artifact scorer, `engines/artifact_score.py`.

Every weight, magnitude and tolerance in this file is a CALLER-SUPPLIED value
chosen by the test. The module under test carries none of them, and the last
three tests prove that by walking its AST. The stat ids used here are the
SYNTHETIC_* placeholders of the hand-authored fixture and plain made-up names;
no real upstream id appears anywhere in this file or in the module.

The fixture's own stat values (7.8, 9.9, 4780.0) are used ONLY as arithmetic
inputs to the weighted sum. Roll counting is exercised on hand-built artifacts
with opaque ids and an arbitrary test magnitude, never against a fixture id,
so no tracked file pairs a fixture-labelled stat with a per-roll figure.

The model under test is stated in `docs/adr/ADR-012-artifact-scoring-model.md`.
Each test below names the ruling it pins.
"""
from __future__ import annotations

import ast
import dataclasses
import json
import math
import random
import re
from pathlib import Path

import pytest

import engines
import engines.artifact_score as module
from core.types import MappedArtifact
from engines.artifact_score import (
    ArtifactScore,
    RollCount,
    WeightedStat,
    rank_artifacts,
    score_artifact,
)
from ingest.enka_mapper import map_profile

FIXTURE = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "enka_sample_profile.json"

#: The fixture's own placeholder ids. They are test data, not a vocabulary.
CRIT_ID = "SYNTHETIC_PROP_CRIT_RATE"
ATK_ID = "SYNTHETIC_PROP_ATTACK_PERCENT"
HP_ID = "SYNTHETIC_PROP_HP"

#: An ARBITRARY per-roll magnitude for the hand-built roll probes. It was
#: chosen for nothing but the arithmetic below and is paired only with opaque
#: made-up ids, never with a fixture id.
ARBITRARY_MAGNITUDE = 2.0


@pytest.fixture(scope="module")
def fixture_artifact() -> MappedArtifact:
    """The one artifact the hand-authored fixture carries, through the real mapper."""
    profile = map_profile(json.loads(FIXTURE.read_text(encoding="utf-8")))
    carried = [artifact for character in profile.characters for artifact in character.artifacts]
    assert len(carried) == 1, f"the fixture is expected to carry exactly one artifact, found {len(carried)}"
    return carried[0]


def _artifact(substats: tuple[tuple[str, float], ...], **over: object) -> MappedArtifact:
    """A hand-built artifact with every field defaulted to something inert."""
    fields: dict[str, object] = {
        "item_id": 1,
        "set_name_hash": "set",
        "rank_level": 1,
        "level": 0,
        "main_stat_id": "main",
        "main_stat_value": 0.0,
        "substats": tuple(substats),
        "equip_type": "slot",
    }
    fields.update(over)
    return MappedArtifact(**fields)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# The weighted sum - R1 to R4
# ---------------------------------------------------------------------------


def test_empty_weights_score_zero_and_list_every_substat_unweighted(fixture_artifact):
    """R4: the fold starts from the float 0.0, so nothing weighted means exactly
    0.0 - including on an artifact with no substats at all, where a fold that
    started from the first value would have nothing to start from."""
    result = score_artifact(fixture_artifact, {})
    assert isinstance(result, ArtifactScore)
    assert result.score == 0.0
    assert type(result.score) is float
    assert result.weighted == ()
    assert result.unweighted == (CRIT_ID, ATK_ID)
    assert result.rolls == ()
    assert result.unresolved == ()
    assert result.main_stat is None
    assert result.artifact is fixture_artifact

    bare = _artifact(())
    empty = score_artifact(bare, {})
    assert empty.score == 0.0
    assert type(empty.score) is float
    assert empty.weighted == ()
    assert empty.unweighted == ()

    also = score_artifact(bare, {"main": 1.0, "elsewhere": 1.0})
    assert also.score == 0.0
    assert also.weighted == ()
    assert also.unweighted == ()


def test_single_weight_returns_that_substats_value(fixture_artifact):
    result = score_artifact(fixture_artifact, {CRIT_ID: 1.0})
    assert result.score == 7.8
    assert result.weighted == (WeightedStat(CRIT_ID, 7.8, 1.0, 7.8),)
    assert result.unweighted == (ATK_ID,)


def test_both_weights_at_one_return_the_sum(fixture_artifact):
    """7.8 + 9.9 == 17.7 holds in double precision, so == is the right assertion."""
    assert 0.0 + 7.8 + 9.9 == 17.7
    result = score_artifact(fixture_artifact, {CRIT_ID: 1.0, ATK_ID: 1.0})
    assert result.score == 17.7
    assert result.weighted == (
        WeightedStat(CRIT_ID, 7.8, 1.0, 7.8),
        WeightedStat(ATK_ID, 9.9, 1.0, 9.9),
    )
    assert result.unweighted == ()


def test_weight_zero_is_weighted_not_unweighted(fixture_artifact):
    """R2: membership decides. A key with weight 0.0 is WEIGHTED at 0.0; only an
    absent key is unweighted. Zero and missing differ."""
    result = score_artifact(fixture_artifact, {CRIT_ID: 0.0})
    assert result.weighted == (WeightedStat(CRIT_ID, 7.8, 0.0, 0.0),)
    assert result.unweighted == (ATK_ID,)
    assert result.score == 0.0


def test_weights_for_absent_stats_are_ignored(fixture_artifact):
    """R3: a priority legitimately covers stats a piece lacks. The typo is made
    visible by `unweighted`, never by an error - but see
    test_bad_magnitude_or_weight_raises: an absent key is still VALIDATED."""
    result = score_artifact(fixture_artifact, {"made_up_stat": 2.5, CRIT_ID: 1.0})
    assert result.score == 7.8
    assert [entry.stat_id for entry in result.weighted] == [CRIT_ID]
    assert result.unweighted == (ATK_ID,)


def test_summation_is_carried_order_and_ignores_weights_mapping_order():
    """R4: a left fold in CARRIED order with plain binary +. The probe values are
    chosen so that the order of addition is observable in the result, which is
    exactly why the rule has to be stated."""
    forward_sum = ((0.0 + 0.1) + 0.2) + 0.3
    backward_sum = ((0.0 + 0.3) + 0.2) + 0.1
    assert forward_sum != backward_sum, "the probe values must make the order observable"

    forward = _artifact((("a", 0.1), ("b", 0.2), ("c", 0.3)))
    backward = _artifact((("c", 0.3), ("b", 0.2), ("a", 0.1)))
    weights_abc = {"a": 1.0, "b": 1.0, "c": 1.0}
    weights_cba = {"c": 1.0, "b": 1.0, "a": 1.0}

    assert score_artifact(forward, weights_abc).score == forward_sum
    assert score_artifact(backward, weights_abc).score == backward_sum
    assert score_artifact(forward, weights_abc) == score_artifact(forward, weights_cba)
    assert [entry.stat_id for entry in score_artifact(backward, weights_cba).weighted] == ["c", "b", "a"]


# ---------------------------------------------------------------------------
# Main stat - R5
# ---------------------------------------------------------------------------


def test_main_stat_excluded_by_default_and_added_last_on_request(fixture_artifact):
    default = score_artifact(fixture_artifact, {HP_ID: 1.0, CRIT_ID: 1.0})
    assert default.score == 7.8
    assert default.main_stat is None
    assert HP_ID not in default.unweighted
    assert all(entry.stat_id != HP_ID for entry in default.weighted)

    on = score_artifact(fixture_artifact, {HP_ID: 1.0}, include_main_stat=True)
    assert on.score == 4780.0
    assert on.main_stat == WeightedStat(HP_ID, 4780.0, 1.0, 4780.0)
    assert on.weighted == ()
    assert on.unweighted == (CRIT_ID, ATK_ID)

    absent = score_artifact(fixture_artifact, {CRIT_ID: 1.0}, include_main_stat=True)
    assert absent.score == 7.8
    assert absent.main_stat is None, "an unweighted main stat leaves `main_stat` None"
    assert absent.unweighted == (ATK_ID, HP_ID), "an unweighted main stat is appended AFTER the substats"

    # Added LAST, and observably so: these values sum differently in the other order.
    main_last = ((0.0 + 0.2) + 0.3) + 0.1
    main_first = ((0.0 + 0.1) + 0.2) + 0.3
    assert main_last != main_first, "the probe values must make the order observable"
    piece = _artifact((("a", 0.2), ("b", 0.3)), main_stat_id="m", main_stat_value=0.1)
    weights = {"a": 1.0, "b": 1.0, "m": 1.0}
    scored = score_artifact(piece, weights, include_main_stat=True)
    assert scored.score == main_last
    assert [entry.stat_id for entry in scored.weighted] == ["a", "b"], "the main stat is reported apart, never in `weighted`"
    assert scored.main_stat == WeightedStat("m", 0.1, 1.0, 0.1)

    # Never roll-counted, even when a magnitude is supplied for its id. Opaque
    # ids and the arbitrary test magnitude; no fixture id is paired with one.
    rollable = _artifact((("a", 5.9), ("b", 1.0)), main_stat_id="m", main_stat_value=4.0)
    rolled = score_artifact(
        rollable,
        {"m": 1.0},
        magnitudes={"m": ARBITRARY_MAGNITUDE, "a": ARBITRARY_MAGNITUDE},
        include_main_stat=True,
    )
    assert [entry.stat_id for entry in rolled.rolls] == ["a"]
    assert rolled.unresolved == ("b",)
    assert rolled.main_stat == WeightedStat("m", 4.0, 1.0, 4.0)


# ---------------------------------------------------------------------------
# Roll counting - R6 to R8
# ---------------------------------------------------------------------------


def test_rolls_are_floor_of_value_plus_tolerance_over_magnitude():
    """R6 and R8 on a hand-built artifact with opaque ids. 2.0 is an arbitrary
    test magnitude; 5.9 / 2.0 == 2.95 exactly in double precision, and 2.95 is
    the probe that tells floor (2) from round (3)."""
    assert 5.9 / ARBITRARY_MAGNITUDE == 2.95
    assert math.floor(5.9 / ARBITRARY_MAGNITUDE) == 2
    assert round(5.9 / ARBITRARY_MAGNITUDE) == 3

    piece = _artifact((("a", 5.9), ("b", 1.0)))
    result = score_artifact(piece, {}, magnitudes={"a": ARBITRARY_MAGNITUDE})
    assert result.rolls == (RollCount("a", 5.9, ARBITRARY_MAGNITUDE, 2.95, 2),)
    assert result.unresolved == ("b",)
    assert result.score == 0.0, "rolls are a layer beside the score, never an input to it"
    assert type(result.rolls[0].rolls) is int

    # R8: tolerance is in STAT units, added to the value before the division,
    # and the quotient excludes it. (5.9 + 0.1) / 2.0 == 3.0 exactly.
    assert (5.9 + 0.1) / ARBITRARY_MAGNITUDE == 3.0
    lenient = score_artifact(piece, {}, magnitudes={"a": ARBITRARY_MAGNITUDE}, tolerance=0.1)
    assert lenient.rolls == (RollCount("a", 5.9, ARBITRARY_MAGNITUDE, 2.95, 3),)
    assert lenient.rolls[0].quotient == 5.9 / ARBITRARY_MAGNITUDE
    assert lenient.unresolved == ("b",)

    # A second value whose quotient sits below one half, so round and floor
    # agree there and the discriminating case above is the one that matters.
    low = score_artifact(_artifact((("a", 0.5),)), {}, magnitudes={"a": ARBITRARY_MAGNITUDE})
    assert low.rolls == (RollCount("a", 0.5, ARBITRARY_MAGNITUDE, 0.25, 0),)


def test_missing_magnitude_lists_stat_unresolved():
    """R6 and R9: a stat with no magnitude is returned, not guessed at, and a
    duplicate id is handled once per carried entry."""
    piece = _artifact((("a", 1.5), ("b", 2.5), ("a", 3.5)))
    result = score_artifact(piece, {"a": 1.0}, magnitudes={"b": 1.0})
    assert [entry.stat_id for entry in result.rolls] == ["b"]
    assert result.unresolved == ("a", "a")
    assert [entry.stat_id for entry in result.weighted] == ["a", "a"]
    assert result.unweighted == ("b",)
    assert result.score == (0.0 + 1.5) + 3.5


def test_bad_magnitude_or_weight_raises():
    """R7: every refusal names the offending stat id or argument, EVERY key of
    `weights` and `magnitudes` is validated whether or not it matches a carried
    stat, and the checks run in a stated order: weights, tolerance, magnitudes,
    then carried values while counting rolls."""
    piece = _artifact((("a", 1.0),))
    inf = float("inf")
    nan = float("nan")

    with pytest.raises(ValueError, match=re.escape(repr("a"))):
        score_artifact(piece, {"a": inf})

    # An absent key is ignored for SCORING (R3) but still validated (R7): the
    # rule-3-only reading would return 1.0 here.
    with pytest.raises(ValueError, match=re.escape(repr("elsewhere"))):
        score_artifact(piece, {"elsewhere": nan})
    with pytest.raises(ValueError, match=re.escape(repr("zz"))):
        score_artifact(piece, {"a": 1.0, "zz": inf})
    with pytest.raises(ValueError, match=re.escape(repr("zz"))):
        score_artifact(piece, {}, magnitudes={"zz": 0.0})

    for bad in (0.0, -1.0, inf, nan):
        with pytest.raises(ValueError, match="magnitude for stat " + re.escape(repr("a"))):
            score_artifact(piece, {}, magnitudes={"a": bad})

    with pytest.raises(ValueError, match="tolerance"):
        score_artifact(piece, {}, magnitudes={"a": 1.0}, tolerance=nan)
    # tolerance is validated even when there is nothing to divide.
    with pytest.raises(ValueError, match="tolerance"):
        score_artifact(piece, {}, tolerance=inf)

    carried_inf = _artifact((("a", inf),))
    with pytest.raises(ValueError, match="carried value for stat " + re.escape(repr("a"))):
        score_artifact(carried_inf, {}, magnitudes={"a": 1.0})
    # ... also when that id has no magnitude of its own.
    with pytest.raises(ValueError, match="carried value for stat " + re.escape(repr("a"))):
        score_artifact(carried_inf, {}, magnitudes={"other": 1.0})

    # Check ORDER on multi-fault inputs: the first offender in weights,
    # tolerance, magnitudes, carried-values order is the one named.
    with pytest.raises(ValueError, match="weight for stat " + re.escape(repr("w"))):
        score_artifact(carried_inf, {"w": nan}, magnitudes={"a": 0.0}, tolerance=nan)
    with pytest.raises(ValueError, match="tolerance"):
        score_artifact(carried_inf, {}, magnitudes={"a": 0.0}, tolerance=nan)
    with pytest.raises(ValueError, match="magnitude for stat " + re.escape(repr("a"))):
        score_artifact(carried_inf, {}, magnitudes={"a": 0.0})

    # Without magnitudes a carried value is taken as-is: the engine does not
    # police the mapper. Ranking, which must order scores, refuses it (R10).
    loose = score_artifact(carried_inf, {"a": 1.0})
    assert loose.score == inf
    with pytest.raises(ValueError, match="non-finite"):
        rank_artifacts([carried_inf], {"a": 1.0})


def test_roll_overflow_raises_value_error_not_overflow_error():
    """R6/R7: an input that passes every finiteness check can still overflow in
    the division. The engine refuses it under the rule-7 shape, naming the
    stat, instead of letting `math.floor` raise `OverflowError`."""
    huge = _artifact((("a", 1e308),))
    assert math.isfinite(1e308) and math.isfinite(1e308 + 0.0)
    assert not math.isfinite((1e308 + 1e308) / 1.0), "the probe must actually overflow"
    with pytest.raises(ValueError, match=re.escape(repr("a"))):
        score_artifact(huge, {}, magnitudes={"a": 1.0}, tolerance=1e308)

    tiny_magnitude = _artifact((("a", 1e300),))
    assert not math.isfinite(1e300 / 1e-10), "the probe must actually overflow"
    with pytest.raises(ValueError, match=re.escape(repr("a"))):
        score_artifact(tiny_magnitude, {}, magnitudes={"a": 1e-10})

    # The same inputs without the roll layer are not the engine's business.
    assert score_artifact(huge, {}).score == 0.0
    assert score_artifact(huge, {}, tolerance=1e308).score == 0.0


def test_roll_quotient_overflow_is_refused_even_when_the_shifted_quotient_is_finite():
    """R6: the QUOTIENT half of the finiteness guard on its own. value and
    tolerance cancel to a finite 0.0, so the shifted quotient is finite and
    floor would give 0, while value / magnitude overflows. A guard that checked
    only the shifted quotient would return quotient inf and rolls 0 instead of
    refusing - the probe every other overflow arm cannot tell apart."""
    assert 1e308 + -1e308 == 0.0
    assert math.isfinite((1e308 + -1e308) / 1e-10)
    assert not math.isfinite(1e308 / 1e-10), "the probe must actually overflow"
    cancelling = _artifact((("a", 1e308),))
    with pytest.raises(ValueError, match=re.escape(repr("a"))):
        score_artifact(cancelling, {}, magnitudes={"a": 1e-10}, tolerance=-1e308)


def test_no_magnitudes_means_no_rolls_and_no_unresolved(fixture_artifact):
    result = score_artifact(fixture_artifact, {CRIT_ID: 1.0})
    assert result.rolls == ()
    assert result.unresolved == ()
    assert score_artifact(fixture_artifact, {CRIT_ID: 1.0}, magnitudes=None) == result

    # An EMPTY mapping is not None: the layer is on and every stat is unresolved.
    empty = score_artifact(fixture_artifact, {CRIT_ID: 1.0}, magnitudes={})
    assert empty.rolls == ()
    assert empty.unresolved == (CRIT_ID, ATK_ID)
    assert empty.score == result.score


# ---------------------------------------------------------------------------
# Ranking - R10, R11
# ---------------------------------------------------------------------------


def test_rank_sorts_by_score_then_full_field_tuple_regardless_of_input_order():
    """R10: score descending, then EVERY MappedArtifact field in declaration
    order. The pieces share one item id on purpose - in the fixture that id is
    a type id common to every piece of one kind, so it cannot break a tie."""
    shared = 90000002
    top = _artifact((("a", 2.0),), item_id=shared, set_name_hash="set_z")
    tie_1 = _artifact((("a", 1.0),), item_id=shared, set_name_hash="set_a", level=0)
    tie_2 = _artifact((("a", 1.0),), item_id=shared, set_name_hash="set_a", level=1)
    tie_3 = _artifact((("a", 1.0),), item_id=shared, set_name_hash="set_b", equip_type="slot_a")
    tie_4 = _artifact((("a", 1.0),), item_id=shared, set_name_hash="set_b", equip_type="slot_b")
    expected = [top, tie_1, tie_2, tie_3, tie_4]
    weights = {"a": 1.0}

    rng = random.Random(20261004)
    for attempt in range(12):
        pool = expected[:]
        rng.shuffle(pool)
        ranked = rank_artifacts(pool, weights)
        assert isinstance(ranked, tuple)
        assert [row.artifact for row in ranked] == expected, f"drift on shuffle {attempt}: {[row.artifact.set_name_hash for row in ranked]}"
        assert [row.score for row in ranked] == [2.0, 1.0, 1.0, 1.0, 1.0]

    # The rows are the same objects score_artifact would produce (R11).
    assert ranked[0] == score_artifact(top, weights)
    # The sort key is the whole field tuple, which astuple spells out.
    assert dataclasses.astuple(tie_1) < dataclasses.astuple(tie_2) < dataclasses.astuple(tie_3) < dataclasses.astuple(tie_4)


def test_rank_refuses_nan_in_any_sort_key_field_and_ties_on_signed_zero():
    """R10 totality. NaN is unordered, so a NaN in ANY float of the sort key
    would make the output depend on input order; ranking refuses it by name.
    -0.0 == 0.0 under Python ordering, so two rows that differ only in the
    sign of a zero compare equal and keep input order - stated, not hidden."""
    nan = float("nan")
    base = _artifact((("a", 1.0),))
    nan_main = _artifact((("a", 1.0),), main_stat_value=nan)
    for order in ([base, nan_main], [nan_main, base]):
        with pytest.raises(ValueError, match="main_stat_value"):
            rank_artifacts(order, {})

    nan_sub = _artifact((("a", 1.0), ("b", nan)))
    # Unweighted, so the SCORE is a finite 0.0 and only the field refusal can fire.
    assert score_artifact(nan_sub, {}).score == 0.0
    with pytest.raises(ValueError, match=re.escape(repr("b"))):
        rank_artifacts([nan_sub], {})
    # Weighted, the score itself is NaN and the score refusal fires first.
    with pytest.raises(ValueError, match="non-finite"):
        rank_artifacts([nan_sub], {"b": 1.0})

    plus = _artifact((("a", 1.0),), main_stat_value=0.0)
    minus = _artifact((("a", 1.0),), main_stat_value=-0.0)
    assert plus == minus, "dataclass equality cannot tell them apart either"
    assert math.copysign(1.0, minus.main_stat_value) < 0.0, "but the bytes differ"
    forward = rank_artifacts([plus, minus], {"a": 1.0})
    backward = rank_artifacts([minus, plus], {"a": 1.0})
    assert [row.artifact is plus for row in forward] == [True, False]
    assert [row.artifact is minus for row in backward] == [True, False]


def test_rank_empty_returns_empty():
    assert rank_artifacts([], {}) == ()
    assert rank_artifacts((), {"a": 1.0}) == ()
    assert isinstance(rank_artifacts([], {}), tuple)


# ---------------------------------------------------------------------------
# Acceptance through the real mapper
# ---------------------------------------------------------------------------


def test_fixture_artifact_scores_through_the_real_mapper(fixture_artifact):
    """The weight acceptance values the decision fixed, against the artifact the
    mapper actually produces from the hand-authored fixture. The fixture's
    values are arithmetic inputs here and nothing more; no magnitude is paired
    with a fixture id."""
    assert fixture_artifact.substats == ((CRIT_ID, 7.8), (ATK_ID, 9.9))
    assert fixture_artifact.main_stat_id == HP_ID

    empty = score_artifact(fixture_artifact, {})
    assert empty.score == 0.0
    assert empty.unweighted == (CRIT_ID, ATK_ID)

    assert score_artifact(fixture_artifact, {CRIT_ID: 1.0}).score == 7.8
    assert score_artifact(fixture_artifact, {CRIT_ID: 1.0, ATK_ID: 1.0}).score == 17.7

    with_main = score_artifact(fixture_artifact, {HP_ID: 1.0}, include_main_stat=True)
    assert with_main.score == 4780.0
    assert with_main.main_stat is not None

    unresolved = score_artifact(fixture_artifact, {}, magnitudes={})
    assert unresolved.rolls == ()
    assert unresolved.unresolved == (CRIT_ID, ATK_ID)

    # The package re-exports the public surface (R12), in the module's own order.
    assert module.__all__ == ["ArtifactScore", "RollCount", "WeightedStat", "rank_artifacts", "score_artifact"]
    for name in module.__all__:
        assert getattr(engines, name) is getattr(module, name), name
        assert name in engines.__all__, name


# ---------------------------------------------------------------------------
# The module ships no number - R14, and the refuter's AST lens
# ---------------------------------------------------------------------------

#: The only numerals the module may spell. 0 == 0.0 and 1 == 1.0, so this set
#: admits both spellings of each.
ALLOWED_NUMERALS = (0, 1)

#: The only modules the scorer may import. An allowlist, not a denylist of I/O
#: modules, so a new import has to be argued for here.
ALLOWED_IMPORTS = frozenset({"__future__", "collections.abc", "dataclasses", "math", "core.types"})

#: An enum-looking string literal - the shape a real upstream prop id takes.
UPPERCASE_LITERAL = re.compile(r"^[A-Z][A-Z0-9_]+$")


def _module_source() -> str:
    return Path(module.__file__).read_text(encoding="utf-8")


def _stray_numerals(source: str) -> list[object]:
    """Every int or float Constant outside the allowed set, plus every negated
    numeric Constant - a spelled `-1` is a hidden number too. Booleans are not
    numerals here even though Python subclasses them from int."""
    stray: list[object] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if node.value not in ALLOWED_NUMERALS:
                stray.append(node.value)
        elif (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and type(node.operand.value) in (int, float)
        ):
            stray.append(-node.operand.value)
    return stray


def _posture_violations(source: str) -> list[str]:
    """Imports outside the allowlist, any call to `open`, and any string literal
    shaped like an upstream prop id."""
    violations: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_IMPORTS:
                    violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module not in ALLOWED_IMPORTS:
                violations.append(f"from {node.module} import ...")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            violations.append("open(...)")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and UPPERCASE_LITERAL.match(node.value):
            violations.append(f"literal {node.value!r}")
    return violations


def test_module_carries_no_numeral_other_than_zero_and_one():
    source = _module_source()
    assert _stray_numerals(source) == []
    walked = [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and type(node.value) in (int, float)
    ]
    assert walked, "the walk found no numeral at all - zero out of zero is not a pass"
    assert set(walked) <= set(ALLOWED_NUMERALS)


def test_the_numeral_arm_can_fail():
    """Non-vacuity: the detector fires on a mutant and stays quiet on the allowed set."""
    assert _stray_numerals("def half(value):\n    return value * 0.5\n") == [0.5]
    assert _stray_numerals("LIMIT = 77\n") == [77]
    assert _stray_numerals("SENTINEL = -1\n") == [-1]
    assert _stray_numerals("ZERO = 0.0\nONE = 1\nALSO = 1.0\nflag = True\nnothing = None\n") == []


def test_module_imports_no_io_and_no_uppercase_prop_literal():
    source = _module_source()
    assert _posture_violations(source) == []
    imported = [
        node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Import | ast.ImportFrom)
    ]
    assert imported, "the walk found no import at all - zero out of zero is not a pass"

    # Non-vacuity, one mutant per lens.
    assert _posture_violations("import json\n") == ["import json"]
    assert _posture_violations("from urllib.request import urlopen\n") == ["from urllib.request import ..."]
    assert _posture_violations("from pathlib import Path\n") == ["from pathlib import ..."]
    assert _posture_violations("import subprocess\n") == ["import subprocess"]
    assert _posture_violations("raw = open('table.json')\n") == ["open(...)"]
    assert _posture_violations("STAT = 'FAKE_PROP_ID'\n") == ["literal 'FAKE_PROP_ID'"]
    assert _posture_violations("from core.types import MappedArtifact\nimport math\nname = 'lower_case'\n") == []
