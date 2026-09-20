"""Guards for the DIRECTORY PRUNING in `_walk_drop`, in `scripts/watch_inbox.py`.

WHY A SEPARATE MODULE. `tests/test_watch_inbox.py` already pins the reparse
point, the entry budget and the digest FORMAT. What it never pinned is the
ordinary-directory arm of the same loop: every child directory that is not a
reparse point went onto the pending list, and `_drop_manifest` sha256s every
file that walk hands back. The walk is reached from the `UserPromptSubmit`
hook, which is a REPEATED trigger and not a timer, and the hook is declared
with a five second ceiling. A killed hook surfaces nothing at all.

WHAT MAKES IT A REAL SHAPE RATHER THAN A HYPOTHETICAL. The drops that arrive on
this channel are `from-<CODE>-verbatim/` directories - a sibling's working-tree
bytes, copied. Measured in the main checkout of this repo on 2026-09-20, with
`find`: 14 `__pycache__` directories within four levels, 149 `.pyc` files in
total, and one each of `node_modules/`, `.mypy_cache/`, `.pytest_cache/` and
`.ruff_cache/`. A sibling that copies a subtree without honouring its ignore
rules ships them, and none of that is correspondence.

THE SET IS NOT DERIVED FROM `.gitignore`, AND AN EARLIER VERSION OF THIS
DOCSTRING SAID IT WAS. Measured with `git check-ignore -v` on 2026-09-20: seven
of the nine names are ignored, and `.git` and `node_modules` are NOT. `.git`
needs no rule because git never tracks its own directory; `node_modules` simply
has none, although `shell/node_modules` exists in this checkout. The two lists
overlap - they are not the same list, and the two names that fall outside it
are among the most expensive to walk.

THE DESIGN CALL, argued rather than assumed. A pruned directory contributes an
ANOMALY LINE, exactly as a reparse point does, and is NOT silently invisible.
The module docstring of the script states the constraint the anomaly line
exists to satisfy: what cannot be digested is forced into every report with its
reason, never keyed silently and never dropped. Silence would also collide two
different facts onto one digest - a drop holding only `__pycache__/` and a drop
holding only `.git/` would key identically, and identically to an empty drop -
and `test_two_different_pruned_directories_do_not_collide_on_one_digest` below
is the arm that would go red if anyone reaches for silence later.

THE BYTE-IDENTICAL-DIGEST INVARIANT SURVIVES THE NAME PRUNE, and that scoping
is load-bearing rather than pedantic. The NAME prune fires on a name match and
on nothing else, so an ordinary drop hashes to exactly what it hashed to before
any of this existed - pinned by
`test_pruning_does_not_move_the_digest_of_an_ordinary_drop`. A drop that DOES
carry a skippable name moves its key once, which it would have done under a
silent skip too, because the files behind that directory stop being digested
either way. Moving once and saying why beats moving once in silence.

THE DEPTH PRUNE IS DIFFERENT AND THE UNSCOPED CLAIM WAS MEASURED FALSE. It CAN
move the digest of a drop containing no skippable name at all. Measured on this
host 2026-09-20: 20 nested PLAIN directories holding one `.md` leaf hash to
`3ad39c51...` with both prunes disabled and to `3bf2207b...` with them live,
because the leaf sits past depth 16. That is the intended trade, and it is
cheap here because the digest format is local - digests live in gitignored
`ops/runtime/` and never travel to a sibling, and the live inbox holds zero
drop directories, so the backfill cost is zero.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "watch_inbox.py"


@pytest.fixture()
def watch(tmp_path):
    """Load the script by path, with every `DEFAULT_` path redirected.

    The redirect is DISCOVERED rather than listed, for the reason spelled out
    at the sibling fixture in `tests/test_watch_inbox.py`: a hand-maintained
    list of things to isolate goes stale the moment somebody adds the next
    `DEFAULT_`, and it fails silently into the operator's live record.
    """
    spec = importlib.util.spec_from_file_location("watch_inbox_pruning_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def _drop(inbox: Path, name: str, files: dict[str, str]) -> Path:
    """A subdirectory payload, the shape `from-RC-verbatim/` arrives in."""
    drop = inbox / name
    drop.mkdir(parents=True, exist_ok=True)
    for rel, body in files.items():
        target = drop / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body.encode("ascii"))
    return drop


# --- the defect itself ------------------------------------------------------


def test_a_bytecode_cache_inside_a_drop_is_not_descended(watch, tmp_path):
    """The characterisation arm. Unpruned, this reports the cache as payload.

    One real file plus a `__pycache__/` holding three compiled artefacts must
    report ONE file. Before the skip set it reported four, and each of the
    three was opened and sha256'd on a five second hook.
    """
    inbox = tmp_path / "inbox"
    drop = _drop(
        inbox,
        "from-XX-verbatim",
        {
            "only.py": "print(1)\n",
            "__pycache__/only.cpython-311.pyc": "bytecode-a\n",
            "__pycache__/other.cpython-311.pyc": "bytecode-b\n",
            "__pycache__/third.cpython-311.pyc": "bytecode-c\n",
        },
    )

    _digest, count, _manifest, _anomalies = watch._drop_manifest(drop)

    assert count == 1, (
        f"the walk descended __pycache__ and reported {count} files for a "
        "one-file drop, hashing every compiled artefact behind it on a hook "
        "with a five second ceiling"
    )


def test_a_pruned_directory_is_named_in_the_report_with_its_reason(watch, tmp_path, capsys):
    """Not descending it is half the fix. Silence about it is the other defect.

    The same two-halves rule the reparse-point arm states, applied to the
    policy skip. An operator who sees a file count drop must be able to read
    WHY from the report rather than reconstruct it.
    """
    inbox = tmp_path / "inbox"
    drop = _drop(
        inbox,
        "from-XX-verbatim",
        {"only.py": "print(1)\n", "__pycache__/only.cpython-311.pyc": "bytecode\n"},
    )
    assert drop.is_dir()
    state = tmp_path / "runtime" / "seen.json"

    watch.main(["--dir", str(inbox), "--state", str(state), "--reported", str(tmp_path / "r.json")])
    out = capsys.readouterr().out

    assert "__pycache__" in out, "the directory was pruned silently, which is the other defect"
    assert watch.REASON_SKIPPED in out, (
        "the report does not say WHY the entry was not descended"
    )


def test_a_pruned_directory_moves_the_drop_digest_rather_than_vanishing(watch, tmp_path):
    """An entry that is not digested must MOVE the key, never drop out of it.

    RE-AIMED AFTER AN ADVERSARY PROVED THE FIRST VERSION VACUOUS. That version
    added a `.pyc` under `__pycache__/` and asserted only that the digest
    moved - which it does under BOTH implementations, because the unpruned walk
    simply digests the `.pyc` as an ordinary file. The arm could not tell the
    fix from its absence, and a gate that cannot fail is not a gate.

    It now asserts the three observables only the pruning produces: the file
    count EXCLUDES what is behind the pruned directory, the anomaly tuple NAMES
    the directory with its reason, and the digest differs from what the same
    tree hashes to when nothing is pruned - that last value rebuilt from the
    documented format rather than from a second implementation.
    """
    import hashlib

    inbox = tmp_path / "inbox"
    drop = _drop(inbox, "from-XX-verbatim", {"only.py": "print(1)\n"})
    before, before_count, _m, before_anoms = watch._drop_manifest(drop)
    assert (before_count, before_anoms) == (1, ())

    (drop / "__pycache__").mkdir()
    (drop / "__pycache__" / "only.cpython-311.pyc").write_bytes(b"bytecode\n")
    after, after_count, _m2, after_anoms = watch._drop_manifest(drop)

    assert after_count == 1, (
        f"the walk digested what was behind __pycache__ and reported "
        f"{after_count} files, which is exactly what the UNPRUNED walk does"
    )
    assert after_anoms == (f"__pycache__: {watch.REASON_SKIPPED}",), (
        f"the pruned directory did not reach the report with its reason: {after_anoms}"
    )
    assert after != before, (
        "a skipped directory appeared inside an acknowledged drop and the key "
        "did not move, so the drop reads as already read"
    )

    unpruned = [
        "only.py" + chr(0) + hashlib.sha256(b"print(1)\n").hexdigest(),
        "__pycache__/only.cpython-311.pyc" + chr(0) + hashlib.sha256(b"bytecode\n").hexdigest(),
    ]
    assert after != hashlib.sha256(chr(10).join(sorted(unpruned)).encode("utf-8")).hexdigest(), (
        "the drop hashes to exactly what an UNPRUNED walk produces, so nothing "
        "was pruned at all"
    )


def test_a_directory_whose_name_differs_only_in_case_is_still_pruned(watch, tmp_path):
    """NTFS preserves case on disk and compares case-insensitively.

    `.GIT/` and `__PYCACHE__/` are the SAME directories as `.git/` and
    `__pycache__/` to every Windows API and to `open()`, and different strings
    to a bare `in`. Measured before the fold: a drop carrying `.GIT/` hashed to
    `d719fe35...` under the case-sensitive prune and to the identical
    `d719fe35...` with the prune removed entirely - the prune never fired, and
    a sender shipping that name got its whole object store digested.

    The similar-name survivor arm below is the other half and must keep
    passing: a casefold must not quietly become a substring match.
    """
    inbox = tmp_path / "inbox"
    for index, name in enumerate((".GIT", "__PYCACHE__", ".Venv", "Node_Modules")):
        drop = _drop(
            inbox,
            f"from-C{index}-verbatim",
            {"only.py": "print(1)\n", f"{name}/buried.txt": "payload\n"},
        )
        _digest, count, _manifest, anomalies = watch._drop_manifest(drop)

        assert count == 1, (
            f"{name}/ was not pruned - the match is case-sensitive and this "
            "platform is not, so a sender shipping that name blows the walk up"
        )
        assert anomalies == (f"{name}: {watch.REASON_SKIPPED}",), (
            f"{name}/ was pruned but the report names it differently: {anomalies}"
        )


def test_two_different_pruned_directories_do_not_collide_on_one_digest(watch, tmp_path):
    """THE ARM THAT ARGUES THE DESIGN CALL, and it is why the anomaly line wins.

    Under a SILENT skip, a drop holding only `__pycache__/` and a drop holding
    only `.git/` both reduce to zero digested files and hash identically - and
    identically to an empty drop. The anomaly line carries the relative path,
    so the three stay distinguishable. Anyone who later replaces the anomaly
    with silence to protect the digest will land here.
    """
    inbox = tmp_path / "inbox"
    left = _drop(inbox, "from-XX-verbatim", {"__pycache__/a.pyc": "x\n"})
    right = _drop(inbox, "from-YY-verbatim", {".git/config": "x\n"})
    bare = _drop(inbox, "from-ZZ-verbatim", {})

    left_digest, left_count, _m, _a = watch._drop_manifest(left)
    right_digest, right_count, _m2, _a2 = watch._drop_manifest(right)
    bare_digest, bare_count, _m3, _a3 = watch._drop_manifest(bare)

    assert (left_count, right_count, bare_count) == (0, 0, 0)
    assert left_digest != right_digest, "two different pruned directories key identically"
    assert left_digest != bare_digest, "a pruned directory keys as an empty drop"
    assert right_digest != bare_digest, "a pruned directory keys as an empty drop"


# --- the invariant the fix must not break -----------------------------------


def test_pruning_does_not_move_the_digest_of_an_ordinary_drop(watch, tmp_path):
    """THE LOAD-BEARING INVARIANT. No existing key may move.

    The expected value is rebuilt here from the DOCUMENTED format - relative
    posix path, NUL, sha256 - rather than copied out of the implementation, so
    this goes red if the format moves even when the implementation agrees with
    itself. An ordinary SUBDIRECTORY is included on purpose: pruning must fire
    on the skip set and on nothing else.
    """
    inbox = tmp_path / "inbox"
    payload = {"a.py": "print(1)\n", "sub/b.txt": "two\n", "sub/deep/c.txt": "three\n"}
    drop = _drop(inbox, "from-XX-verbatim", payload)

    lines = [
        rel + chr(0) + hashlib.sha256(body.encode("ascii")).hexdigest()
        for rel, body in payload.items()
    ]
    expected = hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()

    digest, count, _manifest, anomalies = watch._drop_manifest(drop)

    assert anomalies == (), f"an ordinary drop reported an anomaly: {anomalies}"
    assert count == 3
    assert digest == expected, (
        "the drop manifest format moved for a drop with NO skippable "
        "directory. Every seen key for every drop in every sibling's watermark "
        "just became stale, and the next report dumps the whole inbox back on "
        "the operator as unread"
    )


# --- non-vacuity: the guard must be able to fire ----------------------------


def test_non_vacuity_the_skip_set_is_populated_and_every_member_actually_prunes(
    watch, tmp_path
):
    """A gate that cannot fail is not a gate.

    Two halves, and both are needed. The MEMBERSHIP half names two entries
    outright, so emptying `PRUNED_DIR_NAMES` goes red on a named assertion
    rather than degenerating into a loop over nothing - a loop over an empty
    set passes, which is the exact fixture-excludes-the-defect shape this tree
    has been bitten by. The BEHAVIOUR half then walks a real drop per member,
    so a name that is in the set but not consulted by `_walk_drop` is red too.
    """
    names = watch.PRUNED_DIR_NAMES

    assert len(names) >= 4, f"the skip set is empty or near-empty, so every arm above is vacuous: {names}"
    assert "__pycache__" in names, "the measured 14-directory case is not covered"
    assert ".git" in names, "a sibling's whole object store would be digested"

    inbox = tmp_path / "inbox"
    for index, name in enumerate(sorted(names)):
        drop = _drop(
            inbox,
            f"from-X{index}-verbatim",
            {"only.py": "print(1)\n", f"{name}/buried.txt": "payload\n"},
        )
        _digest, count, _manifest, anomalies = watch._drop_manifest(drop)

        assert count == 1, f"{name} is in the skip set but the walk descended it"
        assert any(name in rel for rel, _reason in [a.split(": ", 1) for a in anomalies]), (
            f"{name} was pruned without an anomaly line naming it"
        )


def test_non_vacuity_an_ordinary_directory_with_a_similar_name_still_survives(watch, tmp_path):
    """THE SURVIVOR ARM. A sweep that prunes everything scores 100 percent.

    `pycache`, `git`, `venv-notes` and `node_modules_readme` are legitimate
    names that must still be walked. Without this arm a skip set implemented as
    a substring match would pass every arm above.
    """
    inbox = tmp_path / "inbox"
    drop = _drop(
        inbox,
        "from-XX-verbatim",
        {
            "pycache/a.txt": "one\n",
            "git/b.txt": "two\n",
            "venv-notes/c.txt": "three\n",
            "node_modules_readme/d.txt": "four\n",
        },
    )

    _digest, count, _manifest, anomalies = watch._drop_manifest(drop)

    assert count == 4, (
        f"a legitimate directory was pruned as collateral: {count} of 4 files "
        f"survived, anomalies {anomalies}"
    )
    assert anomalies == ()


# --- the depth bound --------------------------------------------------------


def test_a_drop_nested_past_the_depth_bound_stops_and_says_so(watch, tmp_path):
    """The walk has an ENTRY budget and had no DEPTH bound. Probed, not assumed.

    The two are not interchangeable. `MAX_DROP_ENTRIES` is a GLOBAL counter:
    once it trips, `pending` is cleared and the WHOLE drop reports as partial,
    so one pathological branch costs the measurement of every sibling branch.
    The depth bound prunes the one branch and leaves the rest measured. It also
    stops the walk before Windows path length turns a shape this tool chose not
    to bound into an `OSError` that reports as `REASON_UNWALKABLE` and blames
    the box.
    """
    bound = watch.MAX_DROP_DEPTH
    assert bound >= 8, f"a bound this tight prunes ordinary payloads: {bound}"

    inbox = tmp_path / "inbox"
    chain = "/".join(f"d{i}" for i in range(bound + 3))
    drop = _drop(inbox, "from-XX-verbatim", {"top.py": "print(1)\n", f"{chain}/buried.txt": "x\n"})

    _digest, count, _manifest, anomalies = watch._drop_manifest(drop)

    assert count == 1, f"the walk went past its own depth bound and digested {count} files"
    assert any(watch.REASON_DEPTH in a for a in anomalies), (
        f"the depth prune was silent: {anomalies}"
    )


def test_non_vacuity_a_drop_just_inside_the_depth_bound_is_fully_digested(watch, tmp_path):
    """The survivor arm for the depth bound.

    A bound that prunes at depth 1 would pass the arm above. This pins the
    other edge: the deepest legitimate file is still counted.
    """
    bound = watch.MAX_DROP_DEPTH
    inbox = tmp_path / "inbox"
    chain = "/".join(f"d{i}" for i in range(bound - 1))
    drop = _drop(inbox, "from-XX-verbatim", {"top.py": "print(1)\n", f"{chain}/leaf.txt": "x\n"})

    _digest, count, _manifest, anomalies = watch._drop_manifest(drop)

    assert count == 2, f"a payload inside the bound was pruned: {count} files, {anomalies}"
    assert anomalies == ()


# --- the vocabulary stays discoverable --------------------------------------


def test_the_new_reasons_are_distinct_from_every_existing_reason(watch):
    """A duplicated reason string makes two different facts unreadable apart.

    `REASON_REPARSE` means the walk refused a link. `REASON_SKIPPED` means it
    refused a name by policy. `REASON_DEPTH` means it refused a level. An
    operator reads these off the report and has to be able to act on them
    differently.
    """
    reasons = [getattr(watch, n) for n in dir(watch) if n.startswith("REASON_")]

    assert len(reasons) == len(set(reasons)), f"two REASON_ constants share a string: {reasons}"
    assert watch.REASON_SKIPPED in reasons
    assert watch.REASON_DEPTH in reasons
