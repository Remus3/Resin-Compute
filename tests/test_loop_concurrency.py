r"""Cross-repo parity guard for the vendored headless-loop concurrency governor.

WHAT IS BEING GUARDED.

`ops/loop/slots.py` and `ops/loop/winmutex.py` are BYTE-IDENTICAL-BY-CONTRACT
across three repositories - Legion Wallpaper, Riot Commander and Resin Compute.
The participating loops do not talk to each other over any API. They coordinate
THROUGH the on-disk protocol in `slots.py`, against ONE shared token bucket at
`C:\ProgramData\lw-loop\slots`, and through the Win32 named-mutex namespace in
`winmutex.py`. Both are namespaces, not interfaces: nothing checks that the
participants agree, so a divergence produces no error anywhere. It produces a
silent concurrency bug - two loops that each believe they are inside the bound
while together they are outside it.

TWO OF THE THREE ACTUALLY ACQUIRE. Legion Wallpaper and Riot Commander both call
`slots.hold()` from their loop controllers against the live bucket. THIS REPO
DOES NOT: it has no executor loop, and the only callers of `hold()` here are the
tests in this file, which run against a `tmp_path` bucket. So this file guards a
PARITY CONTRACT JOINED AHEAD OF NEED. Do not read it as evidence that this repo
throttles anything today.

That is why the pin is on BYTES rather than on behaviour. Behaviour tests catch
a copy that is broken; only a digest catches a copy that is merely DIFFERENT,
which is the failure mode that actually happens when one repo lands a change and
the others do not. Note the limit of that division of labour, measured rather
than assumed: an adversarial pass built a mutant that removed `hold()`'s queueing
entirely and it passed every behaviour arm here until the dropped
`assert not failures` was restored. Behaviour arms only catch what they assert.

WHY THIS FILE READS NO SIBLING TREE, AND WILL NOT BE "IMPROVED" TO.

Riot Commander's equivalent module compares this repo's copies against the live
`C:\Legion Wallpaper` tree. Its own comments record what that cost: Legion
Wallpaper's directory was renamed, the comparison's path stopped resolving, the
guards degraded to a SKIP, and both of them sat silently green from the rename
until 2026-09-06 while pointing at a directory that no longer existed. A guard
that skips itself when its subject disappears is not a guard.

Here it would be worse than merely useless. A cross-tree read couples THIS
suite's colour to a sibling's working copy, so this repo goes red whenever a
sibling moves first - which is the normal, correct order of a joint re-pin, and
also happens for reasons that are none of this repo's business (a sibling being
mid-edit, checked out to a branch, archived, or simply absent on this machine).
Every constant below is therefore self-contained: this repo's CI can prove
parity from ONE checkout, against a value all three sides agreed to.

WHAT A DIGEST STRUCTURALLY CANNOT COVER.

The lane width is not in either file. `slots.py` takes `max_slots` as an
argument, by design - "nothing here may reference any of them: every
project-specific value arrives as an argument". So the number each repo passes
is a separate agreement, pinned separately at the bottom of this file. If the
two sides ever disagree, the effective ceiling on the box becomes the LARGER
value and the governor is theatre.
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from functools import cache
from pathlib import Path

import pytest

from core import config as core_config

ROOT = Path(__file__).resolve().parents[1]
LOOP_DIR = ROOT / "ops" / "loop"

# The bucket every participating repo must point at. Restated here as a literal
# ONCE, deliberately: this is the pin, and a pin that reads its expected value
# out of the thing it is pinning proves nothing. Everywhere ELSE in this module
# the root arrives from `tmp_path`, and `slot_root` below enforces that no test
# can touch the real bucket.
SHARED_BUCKET = Path(r"C:\ProgramData\lw-loop\slots")

# The shared mutex names, restated for the same reason. These are OS namespace
# keys: two repos spelling them differently do not collide and do not error -
# they serialize against nothing at all, each holding a private lock while
# believing it holds the shared one.
SHARED_GEMINI_MUTEX = "Global\\LWRC_GEMINI"
SHARED_GPU_MUTEX = "Global\\LW_GPU"

# The agreed lane width. Same value in Riot Commander and Legion Wallpaper.
EXPECTED_LANES = 3

# The COMPLETE vendored set, restated as an independent literal for exactly the
# reason the constants above are. `SHARED_SHA256` is a dict, and every guard
# that iterates it inherits whatever it happens to contain - so DELETING one
# entry disarms that file's presence check and its digest check together, in a
# single edit, and the only visible trace is the collected count dropping by
# one. Measured on an adversarial pass against 690d8b7: removing the
# `winmutex.py` entry while also corrupting `winmutex.py` gave 18 passed, exit
# 0, zero skips and zero warnings. This tuple is the second, independent witness
# that turns that into a RED.
VENDORED_MODULES = ("slots.py", "winmutex.py")


# ---------------------------------------------------------------------------
# 1. The byte pin
# ---------------------------------------------------------------------------

# RE-PINNING IS A JOINT ACT. These are not local checksums to be regenerated
# when they go red. See the assertion message below for the procedure - the
# short version is that all three repos change in ONE round, each re-hashing
# from its OWN disk, and nobody trusts a digest quoted in a hand-off note.
SHARED_SHA256 = {
    # Vendored 2026-09-06, when Resin Compute took the slot vacated by the
    # archived Red Moon. Legion Wallpaper authored the bytes and carried the
    # red window; this repo copied them BYTE-WISE off the live tree and these
    # digests were re-hashed from this repo's own disk, not copied from the
    # hand-off note. The bucket stays at 3 participants because it models
    # ANTHROPIC ACCOUNT concurrency and the participant count did not change.
    "slots.py": "1c4f8af43ff349709c11bf3fe622e922b24cb720771c49a522b13a4d5e58c492",
    "winmutex.py": "f1b4b011112685efb88616c52752657cf896fbb0993b2d2d264e7b3edde8b4f4",
}


def test_the_vendored_governor_is_present():
    """Absence must be RED, never a skip.

    Every other guard in this file is downstream of these two files existing.
    If a missing vendor drop were allowed to skip, deleting `ops/loop/` would
    take the entire parity contract green-and-silent, which is precisely the
    renamed-directory failure described in the module docstring.
    """
    missing = [name for name in sorted(VENDORED_MODULES) if not (LOOP_DIR / name).is_file()]
    assert not missing, (
        f"{missing} absent from {LOOP_DIR}. This repo has JOINED a machine-wide "
        "concurrency bucket shared with Legion Wallpaper and Riot Commander, both of "
        "which acquire against it for real. This repo does not acquire yet, so losing "
        "these files breaks no running loop here - it silently drops this repo out of "
        "the parity contract, and the drop would surface only when an executor loop is "
        "finally built against a governor nobody kept in sync. Re-vendor them byte-wise "
        "from a sibling tree - do not re-author them, and do not delete this test."
    )


def test_the_pin_covers_every_vendored_module_and_nothing_was_added():
    """Guards the guard: the pin must cover the DIRECTORY, not merely itself.

    Three ways the contract rots with every other arm still green, all three
    demonstrated by two independent adversarial passes against 690d8b7:

      1. an entry is DELETED from `SHARED_SHA256`. Both the presence arm above
         and the digest arm below iterate that one dict, so a single deleted
         line disarms both for that file at once. Measured: delete the
         `winmutex.py` entry AND corrupt `winmutex.py`, and the suite reports
         18 passed, exit 0, zero skips, zero warnings. The only trace is a
         collected count dropping by one, and this repo forbids restating suite
         counts in docs, so nothing anywhere would notice.
      2. `ops/loop/__init__.py` is added - forbidden in prose by the comment on
         `_load` that nothing enforced. Measured: 19 passed, green.
      3. a THIRD module is vendored by a sibling and not here, or a local helper
         is dropped into the verbatim vendor drop. Measured: 19 passed, green.

    One root cause - the pin named FILES instead of the DIRECTORY - so all three
    close together. `VENDORED_MODULES` is the independent second witness; Riot
    Commander's mirror test has always carried its own literal list for exactly
    this reason, and the port to this tree dropped it.
    """
    assert sorted(SHARED_SHA256) == sorted(VENDORED_MODULES), (
        f"SHARED_SHA256 covers {sorted(SHARED_SHA256)} but the vendored set is "
        f"{sorted(VENDORED_MODULES)}. Do not resolve this by editing whichever side "
        "is convenient: removing a digest disarms both the presence and the byte "
        "guard for that file. A module joins or leaves this set only in a joint "
        "round with Legion Wallpaper and Riot Commander."
    )
    on_disk = sorted(path.name for path in LOOP_DIR.glob("*.py"))
    assert on_disk == sorted(VENDORED_MODULES), (
        f"{LOOP_DIR} holds {on_disk}, expected {sorted(VENDORED_MODULES)}. This "
        "directory is a byte-identical mirror of two sibling trees, so an EXTRA file "
        "here is drift even when every pinned digest still matches - including an "
        "__init__.py, which would also change how the modules import."
    )


@pytest.mark.parametrize("name", sorted(SHARED_SHA256))
def test_vendored_module_matches_the_pinned_cross_repo_digest(name: str):
    """Parity provable from ONE checkout, with no sibling tree on the machine."""
    path = LOOP_DIR / name
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = SHARED_SHA256[name]
    assert actual == expected, (
        f"{name} no longer hashes to the digest this repo agreed with Legion Wallpaper "
        f"and Riot Commander.\n"
        f"  expected {expected}\n"
        f"  actual   {actual}\n"
        f"  file     {path}\n"
        "\n"
        "ops/loop/ is BYTE-IDENTICAL-BY-CONTRACT across all three repos. They coordinate "
        "through this file's on-disk protocol against ONE shared bucket, so a divergence "
        "is not a merge conflict anybody sees - it is a silent concurrency bug.\n"
        "\n"
        "DO NOT re-hash the local file to make this green. A local regeneration launders "
        "a unilateral drift into 'agreed' and turns this guard into a rubber stamp. "
        "RE-PINNING IS A JOINT ACT, all three repos in ONE round: agree the new bytes; "
        "copy them BYTE-WISE into every tree (a text write CRLF-mangles them on Windows "
        "and this pin is on bytes); re-hash from EACH tree's OWN disk rather than "
        "trusting the digest in anyone's hand-off note; confirm all three agree; then "
        "update this dict and its counterpart in the other two repos in the same round."
    )


# ---------------------------------------------------------------------------
# 2. Loading the vendored modules
# ---------------------------------------------------------------------------
#
# By path, via importlib. There is no `ops/loop/__init__.py` and one must not be
# added: the directory is a verbatim vendor drop, and adding a file to it makes
# it something this repo authored. Loading by path also keeps these tests
# honest about WHICH bytes they exercise - the ones the digest above pinned,
# read off disk, not whatever an import cache resolved.


@cache
def _load(name: str):
    path = LOOP_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"resin_loop_{name}_under_test", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot build an import spec for the vendored {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def slots():
    return _load("slots")


@pytest.fixture(scope="session")
def winmutex():
    return _load("winmutex")


@pytest.fixture
def slot_root(tmp_path: Path) -> Path:
    """A private, empty bucket for one test - never the real one.

    THE HAZARD THIS CLOSES. The bucket is machine-wide and live: a real headless
    cycle in any of the three repos may be holding slots in it right now. A test
    that acquired there would take a lane away from production work, and a test
    that reaped there would hand a second repo a slot the first still believes
    it holds - the exact double-booking this whole module exists to prevent.
    The assertion is cheap and is the only thing standing between a careless
    edit and that outcome.
    """
    root = tmp_path / "slots"
    assert root != SHARED_BUCKET, "a test must never operate on the real shared bucket"
    root.mkdir()
    return root


def _write_lock(root: Path, index: int, pid: int, *, age: float = 0.0) -> Path:
    """Plant a lock by hand, so the reaper's inputs are exactly what we chose."""
    path = root / f"{index}.lock"
    record = {
        "pid": pid,
        "repo": "resin-compute",
        "run_id": "planted-by-test",
        "cycle": 1,
        "ts": time.time() - age,
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _exited_process() -> subprocess.Popen:
    """A process that has certainly exited, whose pid is certainly not reused.

    Returned as the live `Popen` rather than a bare int ON PURPOSE. Windows frees
    a pid for reuse once the last handle to the process closes, and `Popen` holds
    one; letting the object fall out of scope reintroduces the reuse race this
    helper exists to avoid. Callers must keep the returned object alive for the
    duration of the assertion.

    Exit code 0 also matters: `pid_alive` reads `GetExitCodeProcess` and treats
    259 (STILL_ACTIVE) as alive, so a child that happened to exit 259 would look
    like a running process.
    """
    proc = subprocess.Popen(
        [sys.executable, "-c", "pass"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert proc.wait(timeout=60) == 0, "the sacrificial child must exit cleanly, and not 259"
    return proc


# ---------------------------------------------------------------------------
# 3. The bound itself
# ---------------------------------------------------------------------------


def test_contending_threads_never_exceed_max_slots(slots, slot_root: Path):
    """The core invariant, plus a deterministic proof that contention happened.

    WHY A LATCH AND NOT A BARRIER. The obvious way to force real overlap is a
    `threading.Barrier(max_slots)` inside the critical section - it can only
    release if that many holders are genuinely inside at once. It is also
    WRONG here, and measurably so: it assumes holders arrive in clean waves of
    exactly `max_slots`. They do not, because a released slot is re-acquired by
    a waiting thread while the previous wave is still draining. The grouping
    slips, one holder ends up waiting for a partner that never comes, and the
    barrier times out and breaks for everyone. Measured on this tree at 8
    workers over 2 slots: roughly one run in three stalled for the full barrier
    timeout, so the guard was a coin-flip dressed as a proof.

    An `Event` is monotonic - once set it stays set - so it has no grouping to
    slip. The first holder waits; the one that brings `live` up to `max_slots`
    sets it and everybody proceeds, now and forever after. Capacity is therefore
    reached from an EMPTY bucket before any release has happened, which also
    makes the non-vacuity arm immune to the release-path defect noted below.

    WHAT THIS TEST DELIBERATELY DOES NOT ASSERT, so nobody reads coverage into
    it: that the bucket is empty afterwards. Under contention on Windows the
    vendored `hold()` leaks lockfiles - see the release tests below for the
    uncontended contract, and the slice report for the mechanism. Asserting a
    drained bucket here would make this suite red for a defect in a file this
    repo is forbidden to edit unilaterally, which is a three-repo change, not a
    test fix. `entered == workers` is left out for the same reason: it fails
    outright once every slot has leaked.
    """
    max_slots = 2
    workers = 2 * max_slots

    guard = threading.Lock()
    at_capacity = threading.Event()
    live = 0
    peak = 0
    entered = 0
    failures: list[BaseException] = []

    def worker() -> None:
        nonlocal live, peak, entered
        try:
            with slots.hold(max_slots=max_slots, root=slot_root, repo="resin-compute",
                            run_id="parity", cycle=1, backoff=0.02, jitter=0.02,
                            timeout=60.0):
                with guard:
                    live += 1
                    entered += 1
                    peak = max(peak, live)
                    full = live >= max_slots
                if full:
                    at_capacity.set()
                # Bounded, and self-releasing on expiry: a governor that admits
                # fewer than max_slots must fail the peak assertion below, never
                # hang the suite waiting for a holder that will never arrive.
                if not at_capacity.wait(timeout=30.0):
                    at_capacity.set()
                with guard:
                    live -= 1
        except (slots.SlotTimeout, OSError) as exc:
            failures.append(exc)
            at_capacity.set()

    threads = [threading.Thread(target=worker, name=f"slotter-{i}") for i in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=180)

    assert not [t for t in threads if t.is_alive()], "a worker hung; the governor deadlocked"
    assert peak <= max_slots, (
        f"{peak} holders were inside the bucket at once with max_slots={max_slots}. "
        "The bucket is machine-wide and shared with two other repos, so an over-serve "
        "here is an over-serve of a rate-limit pool none of them controls alone."
    )
    assert peak == max_slots, (
        f"peak concurrency was {peak}, not {max_slots} - the bound was never actually "
        f"exercised, so this test proved nothing about it. Worker failures: {failures!r}"
    )
    assert entered >= max_slots, f"only {entered} workers were ever admitted"
    # RESTORED after an adversarial pass REFUTED this test at 690d8b7. Riot
    # Commander asserts this (its `assert not errors`); the port to this tree
    # collected `failures` and then never asserted on it, mentioning it only
    # inside another assertion's failure message - so it was load-bearing
    # nowhere. The demonstrated hole: mutate `hold()` so the deadline check
    # becomes `if deadline is not None:` and the governor stops QUEUEING
    # entirely, raising SlotTimeout on the first full pass instead of waiting.
    # Every arm above still passes, because the two holders the mutant does
    # admit satisfy both `peak == max_slots` and `entered >= max_slots`, while
    # the two starved workers land silently in `failures`. That mutant fails
    # Riot Commander's suite and passed this one: 19 passed, exit 0.
    #
    # It cannot flake: a worker only reaches this list on SlotTimeout or OSError,
    # and the adversarial pass measured `failures == []` in 200 of 200 rounds
    # against the file as vendored. If this ever DOES go red, the governor
    # stopped waiting - that is the finding, not a flaky test to relax.
    assert not failures, (
        f"{len(failures)} of {workers} workers never got a lane: {failures!r}. "
        "The contract is that `hold()` BLOCKS with jittered backoff until a slot "
        "frees. A SlotTimeout here means it stopped queueing, which is a failed "
        "cycle for a caller - never permission to proceed unslotted."
    )


def test_a_slot_is_released_after_use(slots, slot_root: Path):
    with slots.hold(max_slots=2, root=slot_root, repo="resin-compute", timeout=60.0) as slot:
        assert slot.exists(), "the lockfile must exist while the block runs"
        held = slot
    assert not held.exists()
    assert list(slot_root.glob("*.lock")) == []


def test_a_slot_is_released_even_when_the_body_raises(slots, slot_root: Path):
    """Release lives in a `finally`, and this is why that matters.

    A leaked lock does not degrade this repo. It permanently narrows a bucket
    two OTHER repos are drawing from, and it is reclaimed only by the stale
    sweep - which is deliberately set to three cycle deadlines, so the damage
    outlives the run that caused it by hours.
    """

    class Boom(RuntimeError):
        pass

    held: list[Path] = []
    with pytest.raises(Boom):
        with slots.hold(max_slots=2, root=slot_root, repo="resin-compute", timeout=60.0) as slot:
            held.append(slot)
            raise Boom("the body exploded")

    assert held, "the block never ran, so this proves nothing about release"
    assert not held[0].exists()
    assert list(slot_root.glob("*.lock")) == []


def test_timeout_raises_rather_than_proceeding_unslotted(slots, slot_root: Path):
    """Exhaustion must be a failed cycle, never permission to run unbounded.

    The planted locks carry THIS process's pid and a fresh timestamp, so the
    reaper cannot rescue the caller: neither the liveness arm nor the age arm of
    `is_stale` fires. That isolation is the point - it forces the timeout path
    to be the only way out.
    """
    max_slots = 2
    planted = [_write_lock(slot_root, i, os.getpid()) for i in range(max_slots)]

    with pytest.raises(slots.SlotTimeout):
        with slots.hold(max_slots=max_slots, root=slot_root, repo="resin-compute",
                        timeout=0.3, backoff=0.02, jitter=0.02):
            pytest.fail("entered the critical section with no slot free")

    assert all(p.exists() for p in planted), "a timed-out caller must not disturb the holders"


def test_a_lock_held_by_a_dead_pid_is_reaped(slots, slot_root: Path):
    """Fail-open: a crashed holder must not deadlock the other two repos.

    The timestamp is FRESH, so age cannot explain the reap. Only pid liveness
    can, which is what makes this a test of the liveness arm rather than of the
    stale-after arm.
    """
    corpse = _exited_process()  # kept alive through the assertions - see the helper
    lock = _write_lock(slot_root, 0, corpse.pid)

    removed = slots.reap(slot_root, 2, slots.DEFAULT_STALE_AFTER)

    assert removed == 1, f"expected the dead holder's lock to be reclaimed, got {removed}"
    assert not lock.exists()
    assert corpse.returncode == 0


def test_a_lock_held_by_a_live_pid_is_not_reaped(slots, slot_root: Path):
    """The other half of the sweep, and the half that has teeth.

    A reaper that reclaims everything scores full marks on the test above while
    handing a second repo a slot the first is still inside. Fail-open is only
    safe while it is narrow.
    """
    lock = _write_lock(slot_root, 0, os.getpid())

    removed = slots.reap(slot_root, 2, slots.DEFAULT_STALE_AFTER)

    assert removed == 0, "a live holder's lock was stolen; two repos now believe they hold it"
    assert lock.exists()


def test_a_lock_older_than_stale_after_is_reaped(slots, slot_root: Path):
    """The age arm, isolated: the pid is this very process, so it is certainly alive."""
    lock = _write_lock(slot_root, 0, os.getpid(), age=10_000.0)

    removed = slots.reap(slot_root, 2, stale_after=1.0)

    assert removed == 1
    assert not lock.exists()


def test_a_corrupt_lock_cannot_wedge_the_bucket_forever(slots, slot_root: Path):
    """The FOURTH arm of `is_stale`, and the one an adversarial pass found untested.

    `is_stale` has four paths: unreadable payload, age, pid liveness, and a
    failed stat. The three above cover age and liveness. This covers the first,
    which is the only one that rescues a HALF-WRITTEN lock - a lockfile whose
    holder died between `os.open` and the `json.dump` that fills it.

    That file has no `pid` and no `ts`, so neither the age arm nor the liveness
    arm can reason about it at all. Without the mtime fallback at
    `slots.py` `_read` -> `is_stale`, an unparseable lock would occupy a lane in
    a bucket shared with two live sibling loops until a human deleted it by
    hand. Riot Commander tests this; the port to this tree dropped it.
    """
    lock = slot_root / "0.lock"
    lock.write_text("{ not json", encoding="utf-8")
    old = time.time() - 10_000.0
    os.utime(lock, (old, old))

    assert slots.is_stale(lock, stale_after=100.0) is True, (
        "an unparseable lockfile older than stale_after must be reclaimable. It "
        "carries no pid and no ts, so the mtime fallback is the ONLY thing that "
        "can free the lane it is occupying."
    )
    assert slots.reap(slot_root, 2, stale_after=100.0) == 1
    assert not lock.exists()


def test_a_corrupt_but_recent_lock_is_left_alone(slots, slot_root: Path):
    """The survivor arm, so the guard above cannot pass by over-reaping.

    A sweep that scores full marks by deleting everything has failed. A corrupt
    lock that is still YOUNG belongs to a holder that may be mid-write right
    now, and stealing its lane is the double-booking the governor exists to
    prevent.
    """
    lock = slot_root / "0.lock"
    lock.write_text("{ not json", encoding="utf-8")

    assert slots.is_stale(lock, stale_after=10_000.0) is False
    assert slots.reap(slot_root, 2, stale_after=10_000.0) == 0
    assert lock.exists()


def test_the_lock_payload_identifies_the_holder(slots, slot_root: Path):
    """Cross-repo debugging depends entirely on this.

    The bucket is one directory shared by three repositories. When it is full,
    the only way to learn WHO is holding a lane - and whether that holder is
    still alive - is to read the lockfile. A payload missing `repo` turns
    "which project is starving the others" into guesswork.
    """
    with slots.hold(max_slots=1, root=slot_root, repo="resin-compute",
                    run_id="run-42", cycle=7, timeout=60.0) as slot:
        record = json.loads(slot.read_text(encoding="utf-8"))

    assert record["pid"] == os.getpid()
    assert record["repo"] == "resin-compute"
    assert record["run_id"] == "run-42"
    assert record["cycle"] == 7
    assert isinstance(record["ts"], (int, float))


def test_pid_alive_agrees_with_reality_in_both_directions(slots):
    corpse = _exited_process()
    assert slots.pid_alive(os.getpid()) is True
    assert slots.pid_alive(corpse.pid) is False
    assert slots.pid_alive(0) is False
    assert slots.pid_alive(-1) is False


# ---------------------------------------------------------------------------
# 4. The shared namespaces
# ---------------------------------------------------------------------------


def test_default_root_is_the_one_shared_bucket(slots):
    """Two buckets would both look healthy, and neither would bound the other.

    This is the failure with no symptom. Each repo's governor would work
    perfectly against its own directory, every test would pass on both sides,
    and the machine-wide ceiling would silently be the SUM of the two.
    """
    assert slots.DEFAULT_ROOT == SHARED_BUCKET, (
        f"the default bucket is {slots.DEFAULT_ROOT!r}, not {SHARED_BUCKET!r}. Every "
        "participating repo must point at the same directory or the bound is per-repo, "
        "which is not a bound at all."
    )


def test_mutex_names_are_the_cross_repo_contract(winmutex):
    """Named mutexes collide only on an exact string match.

    A typo does not raise and does not warn. It creates a second, private mutex
    that exactly one process ever waits on, so every caller acquires instantly
    and the log fills with ACQUIRED lines proving nothing.
    """
    assert winmutex.GEMINI_MUTEX == SHARED_GEMINI_MUTEX
    assert winmutex.GPU_MUTEX == SHARED_GPU_MUTEX


def _unique_test_mutex() -> str:
    """A private name, in the per-session Local namespace.

    NEVER the real GEMINI or GPU names. Those are held by live loops on this
    box, so a test that acquired one would block on production work, and - far
    worse - would itself serialize against a real Gemini call, making the suite
    an unannounced participant in a resource contract it is only supposed to be
    describing. `Local\\` also needs no privilege, unlike `Global\\`.
    """
    return "Local\\ResinComputeParityTest_" + uuid.uuid4().hex


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 named-mutex semantics")
def test_the_mutex_admits_one_thread_at_a_time(winmutex):
    """Windows-only because `winmutex.hold` is a documented no-op elsewhere.

    Off win32 the module yields unheld (and logs UNSERIALIZED), so this exact
    assertion would pass while measuring nothing - the vacuous-green case the
    skipif exists to make visible rather than hide.

    The `entered == workers` arm is the non-vacuity half: exclusion is trivially
    satisfied by a mutex nobody can ever acquire.
    """
    name = _unique_test_mutex()
    workers = 4
    guard = threading.Lock()
    live = 0
    peak = 0
    entered = 0
    failures: list[BaseException] = []

    def worker() -> None:
        nonlocal live, peak, entered
        try:
            with winmutex.hold(name, timeout=60.0):
                with guard:
                    live += 1
                    entered += 1
                    peak = max(peak, live)
                time.sleep(0.02)
                with guard:
                    live -= 1
        except (winmutex.MutexTimeout, OSError) as exc:
            failures.append(exc)

    threads = [threading.Thread(target=worker, name=f"mutexer-{i}") for i in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=180)

    assert not [t for t in threads if t.is_alive()], "a worker hung on the named mutex"
    assert not failures, f"workers raised: {failures!r}"
    assert entered == workers, f"only {entered}/{workers} workers ever acquired the mutex"
    assert peak == 1, f"{peak} threads were inside a mutually exclusive section at once"


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 named-mutex semantics")
def test_mutex_timeout_raises_rather_than_proceeding_unserialized(winmutex):
    """A contended mutex must fail the step, not wave the caller through."""
    name = _unique_test_mutex()
    acquired = threading.Event()
    release = threading.Event()
    holder_failed: list[BaseException] = []

    def holder() -> None:
        try:
            with winmutex.hold(name, timeout=60.0):
                acquired.set()
                release.wait(timeout=60)
        except (winmutex.MutexTimeout, OSError) as exc:
            holder_failed.append(exc)
            acquired.set()

    thread = threading.Thread(target=holder, name="mutex-holder")
    thread.start()
    try:
        assert acquired.wait(timeout=60), "the holder never got in; nothing was contended"
        assert not holder_failed, f"the holder itself failed: {holder_failed!r}"
        with pytest.raises(winmutex.MutexTimeout):
            with winmutex.hold(name, timeout=0.2):
                pytest.fail("entered a mutex-protected section while another thread held it")
    finally:
        release.set()
        thread.join(timeout=60)

    assert not thread.is_alive()


# ---------------------------------------------------------------------------
# 5. The lane width - the agreement no digest can carry
# ---------------------------------------------------------------------------


def test_the_lane_width_matches_the_other_repos():
    """`max_slots` arrives as an argument, so parity of the FILE does not imply
    parity of the NUMBER.

    This is the non-vacuous half of the lane guard: it reads a constant that
    exists in this tree today. If the two sides ever disagree, the effective
    machine-wide ceiling becomes the LARGER of the values - each repo is
    correctly bounded by its own belief, and the bucket is bounded by nobody.
    """
    assert core_config.MAX_CONCURRENT_LANES == EXPECTED_LANES, (
        f"core.config.MAX_CONCURRENT_LANES is {core_config.MAX_CONCURRENT_LANES}, but Riot "
        f"Commander and Legion Wallpaper both pass {EXPECTED_LANES}. Changing this is a "
        "three-repo agreement, not a local tuning knob: the bucket models ANTHROPIC ACCOUNT "
        "concurrency, which is one pool for all three."
    )


def test_the_config_dataclass_defaults_to_the_agreed_lane_width():
    """The constant and the dataclass default must not be able to drift apart."""
    fields = {f.name: f for f in dataclasses.fields(core_config.Config)}
    assert "max_concurrent_lanes" in fields, (
        "core.config.Config has no `max_concurrent_lanes` field, so nothing carries the "
        f"lane width into a live Config. Declared shape: a field defaulting to "
        f"MAX_CONCURRENT_LANES ({EXPECTED_LANES})."
    )
    field = fields["max_concurrent_lanes"]
    default = field.default
    if default is dataclasses.MISSING and field.default_factory is not dataclasses.MISSING:
        default = field.default_factory()
    assert default == core_config.MAX_CONCURRENT_LANES == EXPECTED_LANES, (
        f"Config.max_concurrent_lanes defaults to {default!r}, MAX_CONCURRENT_LANES is "
        f"{core_config.MAX_CONCURRENT_LANES!r}, and the width agreed with Riot Commander and "
        f"Legion Wallpaper is {EXPECTED_LANES!r}. All three must be the same number: two "
        "answers to one question is how the agreed value gets quietly bypassed by whichever "
        "surface a caller happens to reach for."
    )


# Directories the sweep below must not descend into.
#
# `.claude/worktrees/` is the load-bearing one and the reason dot-directories
# are excluded wholesale rather than just `.git`. It holds FULL COPIES of this
# repository, one per in-flight agent. A sweep that walked them would report on
# other agents' uncommitted work - so this suite's colour would depend on what
# an unrelated worktree happens to contain at the moment it runs, which is both
# non-reproducible and none of this test's business.
_SWEEP_SKIP_DIRS = frozenset({"__pycache__", "node_modules", "venv", "build", "dist"})


def _lane_declarations(root: Path) -> dict[str, object]:
    """Every `config*.json` in the tree that declares `max_concurrent_lanes`."""
    found: dict[str, object] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and d not in _SWEEP_SKIP_DIRS
        ]
        for filename in filenames:
            if not (filename.startswith("config") and filename.endswith(".json")):
                continue
            path = Path(dirpath) / filename
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue  # not our file to validate; some other guard owns malformed JSON
            if isinstance(data, dict) and "max_concurrent_lanes" in data:
                found[path.relative_to(root).as_posix()] = data["max_concurrent_lanes"]
    return found


def test_every_json_config_declaring_a_lane_count_declares_the_agreed_one():
    """VACUOUS TODAY, ON PURPOSE, AND SAYING SO IS THE POINT.

    Measured 2026-09-06: this tree contains ZERO `config*.json` files, so this
    sweep inspects nothing and passes on an empty set. It is written now because
    Riot Commander drives its loop from exactly such a file surface, and if that
    surface is ever ported here the lane width would arrive in JSON - a second
    place for the number to live, and the first place it would drift.

    DELIBERATELY NO `assert found`. Riot Commander's copy has that arm because
    Riot Commander has the files; asserting non-emptiness here would be red on
    arrival and would say nothing about lane parity. The non-vacuous half of
    this guard is `test_the_lane_width_matches_the_other_repos` above, which
    reads a constant that does exist. When the first config file lands, add the
    non-emptiness arm in the same change.
    """
    found = _lane_declarations(ROOT)
    disagreeing = {name: value for name, value in found.items() if value != EXPECTED_LANES}
    assert not disagreeing, (
        f"these config files disagree with the agreed lane width of {EXPECTED_LANES}: "
        f"{disagreeing}. All declarations, in JSON and in code, must carry the same number - "
        "the effective ceiling is otherwise the largest of them."
    )
