"""Guards for the two ways `deliver` can stop: a refused draft, a bad path.

THE DEFECT THESE ARMS WERE WRITTEN FOR. `deliver` raises on a draft the gate
refused, and separately loops over inboxes catching `OSError`. `Path.mkdir`
raises `ValueError` - NOT `OSError` - when a path component carries a NUL byte,
measured on 3.14.4 and on the 3.11 also installed here, which is CI's minor. So
a malformed destination mid-loop aborted the whole broadcast with SOME inboxes
written and NO record of which. That partial-and-silent ordering is the one this
function's own docstring names as the worst available.

WHY THE FIX IS NOT "WIDEN THE EXCEPT". The refusal at the top of `deliver` used
a bare `ValueError` as its OWN signal. Absorbing `ValueError` in the loop would
have made a REFUSED DRAFT and a MALFORMED PATH indistinguishable to every
caller, which is a second defect traded for the first. The refusal therefore
gets a distinct type first, and only then may the loop widen.

WHY THAT TYPE STILL DERIVES FROM `ValueError`. Load-bearing, not decorative.
Any caller written before the split catches `ValueError` on exactly this raise,
and a type that did not derive from it would break every one of them for a
reason that has nothing to do with the defect. The arm below asserts the
subclass relation directly rather than leaning on a neighbouring test file to
prove it by accident.

WHY THE TYPE IS PRIVATE. This is a FLEET tool, read by four sibling
repositories. A PUBLIC exception name is a catch surface a sibling can bind to,
and that would make an internal distinction into a cross-repo contract this
tree never agreed to owe.

THE FIXTURES ARE HAND-TYPED. The untagged body below is written out rather than
obtained from `validate_draft`, because a grading arm that consults the same
predicate as the thing it grades measures agreement and not correctness.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"

#: Hand-typed. Carries no responder tag, so the gate refuses it. Written as a
#: literal rather than derived, per the module docstring above.
UNTAGGED_BODY = "a body with no responder tag at all\n"

#: Hand-typed name for every delivery below.
NOTE_NAME = "2026-09-09-1200-from-RSC-reply.md"


@pytest.fixture()
def rsp(tmp_path):
    """Load the responder with every `DEFAULT_*` path redirected into `tmp_path`.

    Same isolation as `tests/test_moon_sync_responder.py`, and for the same
    measured reason: a default that escaped here would not pollute a record, it
    would deliver a note into a sibling's inbox. Discovered rather than listed,
    because a hand-maintained list of things to isolate goes stale silently.
    """
    spec = importlib.util.spec_from_file_location("responder_broadcast_under_test", MODULE)
    assert spec is not None and spec.loader is not None, f"cannot load {MODULE}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def _nul_inbox(tmp_path: Path) -> Path:
    """A destination whose PARENT component carries a NUL byte.

    THE NUL GOES IN A COMPONENT THAT SURVIVES, and that is a measurement rather
    than a preference. `Path.parent` STRIPS a NUL-bearing final component, so a
    NUL placed in the note name would be gone by the time `mkdir` saw the
    directory. It is also why the byte is built here in Python: `os.environ` and
    `sys.argv` both reject an embedded NUL at the process boundary with
    `ValueError`, so neither could have carried one into a test.
    """
    return tmp_path / ("b" + chr(0) + "ad") / "moon_sync_inbox"


def test_the_nul_fixture_really_is_malformed(tmp_path):
    """NON-VACUITY CONTROL for the arms below. The detector must actually fire.

    If `mkdir` on this path quietly succeeded, or raised an `OSError` that the
    original narrow guard already caught, then every arm below would pass while
    measuring nothing. This arm pins the exact fact the defect rests on: the
    raise is a `ValueError` and is NOT an `OSError`.
    """
    bad = _nul_inbox(tmp_path)

    with pytest.raises(ValueError) as caught:
        bad.mkdir(parents=True, exist_ok=True)

    assert not isinstance(caught.value, OSError), (
        "mkdir raised an OSError, so the original narrow guard would have caught it "
        "and this defect would not exist"
    )
    assert chr(0) in str(bad.parent), "the NUL was stripped, so this fixture is inert"


def test_a_refused_draft_raises_the_distinct_refusal_type(rsp, tmp_path):
    """The gate's refusal has its OWN type, not a bare `ValueError`."""
    dest = tmp_path / "a" / "moon_sync_inbox"
    dest.mkdir(parents=True)

    with pytest.raises(rsp._DraftRefused):
        rsp.deliver(UNTAGGED_BODY, NOTE_NAME, [dest], validate=True)

    assert list(dest.iterdir()) == [], "an invalid draft was written anyway"


def test_the_refusal_type_stays_catchable_as_a_valueerror(rsp, tmp_path):
    """Every EXISTING caller that catches `ValueError` must keep working.

    Asserted twice on purpose - the subclass relation, and then the behaviour,
    because the relation is what a reader checks and the behaviour is what a
    caller depends on.
    """
    assert issubclass(rsp._DraftRefused, ValueError)

    dest = tmp_path / "a" / "moon_sync_inbox"
    dest.mkdir(parents=True)

    with pytest.raises(ValueError):
        rsp.deliver(UNTAGGED_BODY, NOTE_NAME, [dest], validate=True)


def test_a_malformed_path_does_not_abort_the_broadcast(rsp, tmp_path):
    """THE DEFECT. A bad inbox in the middle must not strand the ones after it.

    Three inboxes, the SECOND malformed. The first and third are still
    attempted, and the result list carries three entries so the caller learns
    exactly which destination was skipped. No inbox is written without a record,
    and no inbox is skipped without one either.
    """
    first = tmp_path / "first" / "moon_sync_inbox"
    third = tmp_path / "third" / "moon_sync_inbox"
    second = _nul_inbox(tmp_path)

    results = rsp.deliver(UNTAGGED_BODY, NOTE_NAME, [first, second, third])

    assert len(results) == 3, f"the loop aborted mid-broadcast: {results}"
    assert results[0][0] is True, "the inbox BEFORE the malformed one was not written"
    assert results[1][0] is False, "the malformed inbox was reported as written"
    assert results[2][0] is True, "the inbox AFTER the malformed one was never attempted"

    assert (first / NOTE_NAME).read_bytes() == UNTAGGED_BODY.encode("ascii")
    assert (third / NOTE_NAME).read_bytes() == UNTAGGED_BODY.encode("ascii")
    assert [target for _, target in results][1] == second / NOTE_NAME, (
        "the skipped destination is not named in the record, so the caller "
        "cannot tell WHICH inbox it missed"
    )


def test_a_refusal_and_a_malformed_path_are_distinguishable(rsp, tmp_path):
    """THE WHOLE POINT OF THE CHANGE, stated as one arm.

    Both failures were `ValueError` before this. A caller now sees two
    different things: a refusal ESCAPES as `_DraftRefused`, and a malformed path
    does not escape at all - it lands as a `False` row. Neither is mistakable
    for the other.
    """
    good = tmp_path / "good" / "moon_sync_inbox"
    bad = _nul_inbox(tmp_path)

    # A malformed path must NOT raise the refusal type - it is not a refusal.
    try:
        path_results = rsp.deliver(UNTAGGED_BODY, NOTE_NAME, [good, bad])
    except rsp._DraftRefused:  # pragma: no cover - the arm exists to prove it does not fire
        pytest.fail("a malformed path was reported as a refused draft")

    assert [ok for ok, _ in path_results] == [True, False]

    # A refused draft must raise, and must not have written anywhere.
    other = tmp_path / "other" / "moon_sync_inbox"
    with pytest.raises(rsp._DraftRefused):
        rsp.deliver(UNTAGGED_BODY, NOTE_NAME, [other], validate=True)
    assert not other.exists(), "a refused draft created its destination"


# ---------------------------------------------------------------------------
# THE COST OF THE WIDENING, AND THE TWO ARMS THAT BOUND IT.
#
# `except (OSError, ValueError)` is wider than the defect it was written for.
# `UnicodeEncodeError` IS a `ValueError` subclass, and `core/atomic_io.py`'s
# `atomic_write_text` catches only `OSError` - so a draft carrying a lone
# surrogate escaped it LOUDLY before the widening and would be swallowed into a
# plausible-looking `(False, target)` row afterwards. That is a loud-to-quiet
# regression, and a loud-to-quiet regression is strictly worse than the silent
# abort the widening was fixing: the abort at least stopped.
#
# The second arm is the other half. A `(False, target)` row carries THREE
# unrelated meanings - the target already existed, the OS refused, the caller
# passed garbage - and `run_once` reduces the whole list with
# `all(ok for ok, _ in written)`. A caller reading `False` cannot tell which
# happened, so the reason has to reach the log even though the row cannot
# carry it.
# ---------------------------------------------------------------------------

#: Hand-typed. A lone high surrogate, written as an ESCAPE rather than as a
#: literal character, because this tree is 7-bit ASCII by rule and typing the
#: codepoint would make the fixture violate the rule it exists beside. utf-8
#: cannot encode it, which is the whole point.
SURROGATE_BODY = "a body carrying \ud800 and nothing else odd\n"


def test_the_surrogate_fixture_really_is_unencodable(tmp_path):
    """NON-VACUITY CONTROL for the arm below. The detector must actually fire.

    Pins the two facts the arm rests on, either of which failing would make it
    pass while measuring nothing: utf-8 refuses this string, and the refusal is
    a `ValueError` that is NOT an `OSError` - so the widened guard really would
    absorb it if nothing stopped it.
    """
    with pytest.raises(UnicodeEncodeError) as caught:
        SURROGATE_BODY.encode("utf-8")

    assert isinstance(caught.value, UnicodeError), "UnicodeEncodeError is not a UnicodeError"
    assert isinstance(caught.value, ValueError), (
        "UnicodeEncodeError is not a ValueError, so the widened guard never absorbed it "
        "and the arm below is measuring nothing"
    )
    assert not isinstance(caught.value, OSError), "the narrow guard already caught this"


def test_an_unencodable_draft_still_escapes_the_delivery_loop(rsp, tmp_path):
    """LOUD MUST STAY LOUD. The widened guard must not swallow a `UnicodeError`.

    Before the widening this escaped `deliver` as an unhandled
    `UnicodeEncodeError` - ugly, but unmissable. After it, and with no
    re-raise, it becomes a `(False, target)` row indistinguishable from an
    inbox that merely already had the note. That is the regression this arm
    exists to hold shut.

    The check is a TYPE test on purpose. This tree has twice been bitten by a
    widened string matcher, and its standing lesson is that a shape it cannot
    parse must FAIL rather than be matched around.
    """
    dest = tmp_path / "unencodable" / "moon_sync_inbox"

    with pytest.raises(UnicodeError):
        rsp.deliver(SURROGATE_BODY, NOTE_NAME, [dest])


def test_an_absorbed_failure_names_the_target_and_the_exception_class(rsp, tmp_path):
    """A `False` row that says nothing else is an undiagnosable `False`.

    Graded on the LOG BYTES rather than by re-asking the module which
    destinations it thinks failed. Asking the same predicate the code asks
    measures agreement, not correctness.
    """
    good = tmp_path / "good" / "moon_sync_inbox"
    bad = _nul_inbox(tmp_path)

    results = rsp.deliver(UNTAGGED_BODY, NOTE_NAME, [good, bad])
    assert [ok for ok, _ in results] == [True, False], results

    assert rsp.DEFAULT_INVOCATIONS.is_file(), (
        "the absorbed failure left no log line at all, so the caller's False "
        "has no diagnosable cause anywhere"
    )
    logged = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii")

    assert "ValueError" in logged, (
        f"the exception CLASS is not in the log, so the reason is lost: {logged!r}"
    )
    assert NOTE_NAME in logged, (
        f"the skipped target is not named in the log: {logged!r}"
    )
    # HAND-DERIVED, not obtained from the module's own label helper. Asking the
    # code how it spells a path and then checking it spelled it that way is
    # agreement, not correctness. Note the NUL survives verbatim - only TAB and
    # the newlines are substituted, because only those forge a second record.
    assert str(bad / NOTE_NAME) in logged, (
        f"the log does not say WHICH inbox was skipped: {logged!r}"
    )
    assert str(good / NOTE_NAME) not in logged, (
        "the inbox that was written successfully was logged as a failure too, "
        "so the log cannot separate the two"
    )
