"""Characterisation of `_trim_invocations` in `tools/moon_sync_responder.py`.

WHAT THIS FILE PINS, AND WHY IT IS A CHARACTERISATION RATHER THAN A FIX.

`_trim_invocations` is a TRIM, not a rotation. When it fires it atomically
overwrites the ledger with the newest `MAX_INVOCATION_LINES` lines and writes
the discarded lines NOWHERE. The oldest evidence is destroyed. That is the
current behaviour, it is deliberate enough to have a docstring, and nothing
here changes it - these arms exist so that the destruction is a STATED, TESTED
property instead of an accident nobody has ever watched happen.

THE TRIGGER IS THE BYTE CAP ALONE, AND THAT IS THE FINDING THE EXISTING
COVERAGE DOES NOT STATE. `tests/test_moon_sync_responder.py` has one arm on
this path, `test_the_invocation_log_is_bounded_and_keeps_the_newest_lines`,
and it drives a fixture that is over BOTH caps at once. A fixture over both
caps cannot tell the two apart, so it says nothing about which one is load
bearing. Driven separately the two caps turn out not to be peers at all:

  - Over the LINE cap and under the BYTE cap, the function returns at its
    `stat` and the ledger is UNCHANGED. `MAX_INVOCATION_LINES` is not a
    trigger. It is only the keep-count applied once the byte cap has already
    fired.
  - Over the BYTE cap and under the LINE cap, the function fires, keeps every
    line, and rewrites the file anyway - leaving it still over the byte cap it
    was invoked to enforce.

WHY THE PATH IS UNEXERCISED IN PRACTICE. Measured in the main tree on
2026-09-10, `ops/runtime/responder_invocations.log` was 1824 bytes over 48
lines, which is under one percent of `MAX_INVOCATION_BYTES`. The destructive
branch has never fired on this machine, so every claim about it is a claim
about code no operator has seen run. These arms are the only place it runs.

EVERY FIXTURE IS SIZED FROM THE MODULE'S OWN CONSTANTS. Retyping either cap's
literal here would make each arm agree with a number this file invented rather
than with the module, and the arm would then stay green through a constant
change that broke the caller. `test_the_caps_are_read_from_the_module` below
scans this file's own source to keep that honest, and it earned its keep on
first run by failing against an earlier draft of THIS paragraph, which quoted
the byte cap's digits in prose.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"


@pytest.fixture()
def rsp(tmp_path):
    """The responder with every `DEFAULT_*` path redirected under `tmp_path`.

    Deliberately the same DISCOVERED redirection that `tests/test_moon_sync_responder.py`
    uses rather than a hand-written list of the paths this file happens to care
    about. That file records why: a hand-maintained list goes stale the moment
    someone adds the next default, and it fails SILENTLY, because the only arm
    that would have caught the omission is the same list. Here the specific
    stake is `DEFAULT_INVOCATIONS`, which `_trim_invocations` reads off the
    module by name at call time - an un-redirected run would overwrite the
    operator's live invocation ledger with this file's filler and destroy the
    real trial evidence, which is exactly the damage these arms describe.
    """
    spec = importlib.util.spec_from_file_location("moon_sync_responder_trim_under_test", MODULE)
    assert spec is not None and spec.loader is not None, f"cannot load {MODULE}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)

    assert tmp_path in module.DEFAULT_INVOCATIONS.parents, (
        "the invocation ledger still points at live runtime state; every arm "
        "below would then be driving the operator's real evidence file"
    )
    return module


def _line(index: int, width: int) -> str:
    """One synthetic ledger line of exactly `width` characters, carrying its ordinal.

    THE ORDINAL IS THE POINT. Filler made of one repeated string can only ever
    support a COUNT assertion - it cannot say WHICH lines survived, so a trim
    that kept the oldest lines instead of the newest would pass against it. Each
    line here names its own position, so survival and destruction are both
    checkable by identity.
    """
    stem = f"2026-01-01T00:00:00\tseq{index:08d}\t-\tstart"
    assert len(stem) <= width, (stem, width)
    return stem.ljust(width)


def _write_ledger(rsp, count: int, width: int) -> str:
    """Lay down `count` lines of `width` chars each, WITHOUT a trailing newline.

    THE MISSING TRAILING NEWLINE IS LOAD BEARING AND IS NOT AN OVERSIGHT. The
    trim's rewrite is `"".join(f"{line}\\n" for line in lines[-cap:])`, so it
    ALWAYS terminates the file with a newline. Starting from a file that lacks
    one makes "was this file rewritten at all" a byte-level question with a
    yes-or-no answer, instead of a question a content-preserving rewrite could
    answer identically either way. Without it, the two arms below that assert
    the function did NOT fire would pass just as happily against a function
    that fired and happened to keep everything.
    """
    body = "\n".join(_line(i, width) for i in range(count))
    rsp.DEFAULT_INVOCATIONS.parent.mkdir(parents=True, exist_ok=True)
    rsp.DEFAULT_INVOCATIONS.write_bytes(body.encode("ascii"))
    return body


def _all_text_under(root: Path) -> str:
    """Every readable byte anywhere under `root`, concatenated.

    Used to ask whether a discarded line went ANYWHERE, not merely whether it
    left the ledger. A rotation would have put it in a sibling file; a trim puts
    it nowhere. Asserting only that the ledger no longer holds it cannot tell
    those two apart, and telling them apart is the whole finding.
    """
    chunks = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            chunks.append(path.read_text(encoding="ascii", errors="replace"))
    return "\n".join(chunks)


def test_a_ledger_under_both_caps_is_left_byte_for_byte_unchanged(rsp, tmp_path):
    """NEITHER CAP FIRES. The `stat` guard returns before anything is read.

    Falsified by: any rewrite at all. The fixture ends without a newline, which
    the trim's own join can never produce, so a function that reached its write
    would leave a file one byte longer than this assertion allows - whether or
    not it kept every line.
    """
    width = 48
    count = 32
    body = _write_ledger(rsp, count, width)

    size = rsp.DEFAULT_INVOCATIONS.stat().st_size
    assert size <= rsp.MAX_INVOCATION_BYTES, (size, rsp.MAX_INVOCATION_BYTES)
    assert count <= rsp.MAX_INVOCATION_LINES, (count, rsp.MAX_INVOCATION_LINES)

    rsp._trim_invocations()

    assert rsp.DEFAULT_INVOCATIONS.read_bytes() == body.encode("ascii"), (
        "a ledger under both caps was rewritten. The cheap path is a single "
        "`stat`, and losing it means every fire pays a full read of the log"
    )


def test_the_line_cap_alone_never_fires_the_trim(rsp, tmp_path):
    """OVER THE LINE CAP, UNDER THE BYTE CAP - AND NOTHING HAPPENS.

    `MAX_INVOCATION_LINES` is NOT a trigger. The only trigger is the `stat`
    against `MAX_INVOCATION_BYTES`; the line cap is the keep-count applied
    afterwards. So a ledger can sit indefinitely at many times the line cap and
    never be touched, which is the opposite of what the constant's name
    suggests to a reader who has not traced the branch.

    Falsified by: widening the trigger to `or len(lines) > MAX_INVOCATION_LINES`,
    which is the obvious "fix" to this asymmetry. That change trims this fixture
    and this arm goes red - which is the point. It is a characterisation, so if
    someone deliberately makes the line cap a trigger, this arm is the record of
    what the behaviour used to be and it should be rewritten, not deleted.
    """
    count = rsp.MAX_INVOCATION_LINES + 50
    width = 48
    if (count * (width + 1)) > rsp.MAX_INVOCATION_BYTES:
        pytest.fail(
            "the constants no longer admit a ledger that is over the line cap "
            "and under the byte cap, so this arm cannot be driven: "
            f"lines={rsp.MAX_INVOCATION_LINES} bytes={rsp.MAX_INVOCATION_BYTES}"
        )
    body = _write_ledger(rsp, count, width)

    size = rsp.DEFAULT_INVOCATIONS.stat().st_size
    assert size <= rsp.MAX_INVOCATION_BYTES, (size, rsp.MAX_INVOCATION_BYTES)
    assert count > rsp.MAX_INVOCATION_LINES, (count, rsp.MAX_INVOCATION_LINES)

    rsp._trim_invocations()

    assert rsp.DEFAULT_INVOCATIONS.read_bytes() == body.encode("ascii"), (
        "the line cap fired on its own. That is a real behaviour change and not "
        "a bug fix: the byte `stat` is the documented cheap trigger"
    )
    survivors = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii").splitlines()
    assert len(survivors) == count, (
        f"lines were dropped without the byte cap being crossed: {len(survivors)} of {count}"
    )


def test_over_the_byte_cap_the_oldest_lines_are_destroyed_and_archived_nowhere(rsp, tmp_path):
    """BOTH CAPS ENGAGED - the byte cap triggers, the line cap decides the keep.

    THIS IS THE DESTRUCTIVE PATH, ASSERTED AS DESTRUCTION RATHER THAN AS A
    SURVIVOR COUNT. Counting survivors is what a grader does when it is watching
    the verdict: `len(lines) == cap` is equally true of a trim, of a rotation
    that spilled the remainder to `responder_invocations.log.1`, and of a
    compressor. Those are three different answers to "where did the evidence
    go", and only one of them is what this function does. So the arm names the
    oldest line by ordinal and sweeps the ENTIRE test tree for it.

    Falsified by: adding any archive, spill file or backup - the swept text
    would then contain the ordinal and the arm goes red. Also falsified by
    keeping the oldest lines instead of the newest, by an off-by-one in the
    slice bound, and by not trimming at all.
    """
    width = 48
    count = max(
        rsp.MAX_INVOCATION_LINES * 2,
        (rsp.MAX_INVOCATION_BYTES // (width + 1)) + 100,
    )
    _write_ledger(rsp, count, width)

    size = rsp.DEFAULT_INVOCATIONS.stat().st_size
    assert size > rsp.MAX_INVOCATION_BYTES, (
        f"the fixture is under the byte cap at {size} bytes, so the trim never "
        "fires and every assertion below would pass without it"
    )
    assert count > rsp.MAX_INVOCATION_LINES, (count, rsp.MAX_INVOCATION_LINES)

    rsp._trim_invocations()

    survivors = rsp.DEFAULT_INVOCATIONS.read_text(encoding="ascii").splitlines()
    assert len(survivors) == rsp.MAX_INVOCATION_LINES, (
        f"kept {len(survivors)}, cap is {rsp.MAX_INVOCATION_LINES}"
    )

    first_kept = count - rsp.MAX_INVOCATION_LINES
    assert survivors[0] == _line(first_kept, width), (
        f"the surviving window starts at the wrong ordinal: {survivors[0]!r}"
    )
    assert survivors[-1] == _line(count - 1, width), (
        f"the newest line did not survive; the trim kept the WRONG END: {survivors[-1]!r}"
    )

    # The destruction, stated three ways so that no single one carries it.
    doomed = [f"seq{i:08d}" for i in (0, 1, first_kept - 1)]
    everywhere = _all_text_under(tmp_path)
    for ordinal in doomed:
        assert ordinal not in everywhere, (
            f"{ordinal} survived somewhere under the test tree. `_trim_invocations` "
            "writes discarded lines NOWHERE - if that has changed, this file is the "
            "record of what it used to do and the docstring above is now wrong"
        )

    siblings = sorted(p.name for p in rsp.DEFAULT_INVOCATIONS.parent.iterdir())
    assert siblings == [rsp.DEFAULT_INVOCATIONS.name], (
        f"the trim left a companion file behind: {siblings}. Either it now rotates, "
        "or an atomic temp was orphaned mid-write"
    )


def test_over_the_byte_cap_but_under_the_line_cap_it_rewrites_and_keeps_everything(rsp, tmp_path):
    """THE BYTE CAP FIRES, THE LINE CAP KEEPS EVERY LINE, AND THE CAP IS NOT MET.

    A ledger of few but very long lines crosses `MAX_INVOCATION_BYTES` while
    staying under `MAX_INVOCATION_LINES`. The `stat` triggers, so the whole file
    is read and atomically rewritten - and then `lines[-MAX_INVOCATION_LINES:]`
    is the entire list, so the rewrite preserves every byte of content and the
    file is STILL over the byte cap it was invoked to enforce. The function has
    no second pass and no byte-wise truncation, so it will do exactly this again
    on the next fire, and on every fire after it.

    That is not a hypothetical shape for this log. `log_invocation` writes the
    note NAME into each line, and nothing bounds a note's filename.

    Falsified by: the branch not firing, which the fixture's missing trailing
    newline makes visible - a file this function has rewritten always ends in
    one. Also falsified by any byte-wise truncation being added, which would
    drop content this arm asserts survives.
    """
    count = max(4, rsp.MAX_INVOCATION_LINES // 4)
    width = (rsp.MAX_INVOCATION_BYTES // count) + 64
    body = _write_ledger(rsp, count, width)

    size = rsp.DEFAULT_INVOCATIONS.stat().st_size
    assert size > rsp.MAX_INVOCATION_BYTES, (size, rsp.MAX_INVOCATION_BYTES)
    assert count <= rsp.MAX_INVOCATION_LINES, (count, rsp.MAX_INVOCATION_LINES)

    rsp._trim_invocations()

    after = rsp.DEFAULT_INVOCATIONS.read_bytes()
    assert after == (body + "\n").encode("ascii"), (
        "expected the untouched content plus exactly one appended newline. A "
        "difference here means either the branch did not fire, or the rewrite "
        "is no longer content-preserving under the line cap"
    )
    assert rsp.DEFAULT_INVOCATIONS.stat().st_size > rsp.MAX_INVOCATION_BYTES, (
        "the trim now meets the byte cap in this branch. That is a behaviour "
        "change - as written it enforces a LINE count and calls the byte count "
        "only a trigger, so a long-lined ledger stays over the cap forever"
    )


def test_the_caps_are_read_from_the_module_and_are_not_retyped_here(rsp):
    """NON-VACUITY FOR EVERY ARM ABOVE, and the one that scores this file itself.

    An arm that retypes a cap's literal is not comparing the module to anything. It is
    comparing the module to a number this file made up, and the two agree by
    construction until the day the module's constant changes - at which point
    the arm keeps passing and the caller is the thing that breaks. So every
    fixture above is SIZED from the module attributes, and this arm proves the
    literals are absent by scanning this file's own bytes.

    Both spellings of each constant are swept, because Python's underscore
    separators mean the same integer has two source forms and a sweep that knew
    only one of them would report CLEAN against the other.
    """
    assert isinstance(rsp.MAX_INVOCATION_BYTES, int), rsp.MAX_INVOCATION_BYTES
    assert isinstance(rsp.MAX_INVOCATION_LINES, int), rsp.MAX_INVOCATION_LINES
    assert rsp.MAX_INVOCATION_BYTES > 0 and rsp.MAX_INVOCATION_LINES > 0

    source = Path(__file__).read_text(encoding="ascii")
    forms = set()
    for value in (rsp.MAX_INVOCATION_BYTES, rsp.MAX_INVOCATION_LINES):
        forms.add(str(value))
        forms.add(f"{value:_d}")

    # NON-VACUITY: the sweep must be able to HIT, or CLEAN means nothing. The
    # control is a planted positive rather than a read of the responder source.
    # That is deliberate on both counts. It is stronger, because it proves the
    # matcher fires rather than proving the responder happens to contain some
    # digits. And it keeps this file out of `responder_reading_modules` in
    # `tools/gate_mutation_runner.py`: an earlier draft read the responder's
    # bytes here and was correctly flagged as an undeclared shape grader, which
    # it is not. `_binds_and_reads_responder` says in its own docstring that a
    # module which imports the responder to exercise its BEHAVIOUR is not a
    # grader of its shape and must not be reported. This file is that, and the
    # classification is now true rather than declared around.
    for form in sorted(forms):
        planted = f"a retyped cap looks like {form} in source"
        assert form in planted, form

    leaked = sorted(f for f in forms if f in source)
    assert not leaked, (
        f"a cap is retyped in this file as {leaked}. Size the fixtures from "
        "rsp.MAX_INVOCATION_BYTES / rsp.MAX_INVOCATION_LINES instead"
    )
