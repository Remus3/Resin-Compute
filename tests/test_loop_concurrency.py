r"""Cross-repo parity guard for the vendored headless-loop concurrency governor.

WHAT IS BEING GUARDED.

`ops/loop/slots.py` and `ops/loop/winmutex.py` are BYTE-IDENTICAL-BY-CONTRACT
but NOT by the same population, so NO CLAIM HERE MAY SCOPE TO THE DIRECTORY.
`slots.py` has FOUR carriers - LW, RC, RSC, SS - all agreeing. `winmutex.py`
has FIVE, those four plus CS, and CS's copy DIVERGES. See `SLOTS_CARRIERS` and
`WINMUTEX_CARRIERS` below. RSC is this tree; Sibling-* resolves in a gitignored map.
The participating loops do not talk to each other over any API. They coordinate
THROUGH the on-disk protocol in `slots.py`, against ONE shared token bucket at
`C:\ProgramData\lw-loop\slots`, and through the Win32 named-mutex namespace in
`winmutex.py`. Both are namespaces, not interfaces: nothing checks that the
participants agree, so a divergence produces no error anywhere. It produces a
silent concurrency bug - two loops that each believe they are inside the bound
while together they are outside it.

THREE OF THE FOUR slots.py CARRIERS ARE MEASURED ACQUIRERS. Sibling-E and
Sibling-C both call `slots.hold()` against the LIVE bucket, and SO DOES THIS REPO: since
`1a6d8da`, `run_daemon` in `headless/runner.py` wraps each LIVE pass in a held
slot. No Claude-executor loop was invented to justify the vendored file - the
daemon loop was already this tree's one repeated executor and gained the governor
it was always supposed to have. So this file no longer guards a parity contract
joined ahead of need: a divergence here now bounds the wrong number of real
passes in THIS tree too, not only in a sibling's. The callers of `hold()` inside
THIS file still run against a `tmp_path` bucket and must keep doing so; the arms
about the live acquirer are in `tests/test_headless_runner_slots.py`.

That is why the pin is on BYTES rather than on behaviour. Behaviour tests catch
a copy that is broken; only a digest catches a copy that is merely DIFFERENT,
which is the failure mode that actually happens when one repo lands a change and
the others do not. Note the limit of that division of labour, measured rather
than assumed: an adversarial pass built a mutant that removed `hold()`'s queueing
entirely and it passed every behaviour arm here until the dropped
`assert not failures` was restored. Behaviour arms only catch what they assert.

WHY THIS FILE READS NO SIBLING TREE, AND WILL NOT BE "IMPROVED" TO.

Sibling-C's equivalent module compares this repo's copies against another
sibling's live checkout by absolute path. Its own comments record what that
cost: that sibling's directory was renamed, the comparison's path stopped resolving, the
guards degraded to a SKIP, and both of them sat silently green from the rename
until 2026-09-06 while pointing at a directory that no longer existed. A guard
that skips itself when its subject disappears is not a guard.

Here it would be worse than merely useless. A cross-tree read couples THIS
suite's colour to a sibling's working copy, so this repo goes red whenever a
sibling moves first - which is the normal, correct order of a joint re-pin, and
also happens for reasons that are none of this repo's business (a sibling being
mid-edit, checked out to a branch, archived, or simply absent on this machine).
Every constant below is therefore self-contained: this repo's CI can prove
parity from ONE checkout, against values whose populations are named below.

WHAT A DIGEST STRUCTURALLY CANNOT COVER.

The lane width is not in either file. `slots.py` takes `max_slots` as an
argument, by design - "nothing here may reference any of them: every
project-specific value arrives as an argument". So the number each repo passes
is a separate agreement with its OWN population - FOUR declarers, listed in
`LANE_WIDTH_DECLARERS` below. If any two disagree, the effective ceiling on the
box becomes the LARGER value and the governor is theatre.
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
# keys: a pair of repos spelling them differently do not collide or error -
# they serialize against nothing at all, each holding a private lock while
# believing it holds the shared one.
# ROTATED 2026-09-07 in the joint round Sibling-E announced at 04:15. The retired
# values were "Global\\LWRC_GEMINI" and "Global\\LW_GPU". They are DEAD NAMES,
# not secrets - they sat in that sibling's public repository for five weeks - so nothing
# here tries to hide them. They are recorded because a judge or log parser keyed
# on a fragment of the OLD name now matches nothing and reports GREEN ON NO
# EVIDENCE, which is how that sibling's own P5 probe failed. RSC was swept for that and
# holds no such consumer; these two literals and the shared file are the only
# sites, and this one is the independent second witness for the assertion below.
SHARED_GEMINI_MUTEX = "Global\\MX-7C41A9E2"
SHARED_GPU_MUTEX = "Global\\MX-2E58D3B6"

# The agreed lane width. Same value in Sibling-C and Sibling-E.
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
# when they go red. See the assertion message below for the procedure - the short
# version is that every carrier OF THE MODULE CONCERNED changes in ONE round (the
# two modules have DIFFERENT carrier sets), each re-hashing from its OWN disk.
SHARED_SHA256 = {
    # Vendored 2026-09-06, when Resin Compute took the slot vacated by the
    # archived Sibling-B. Sibling-E authored the bytes and carried the
    # red window; this repo copied them BYTE-WISE off the live tree and these
    # digests were re-hashed from this repo's own disk, not copied from the
    # hand-off note. The bucket WIDTH stayed 3 because it models ANTHROPIC
    # ACCOUNT concurrency. A WIDTH is not a PARTICIPANT COUNT - see below.
    #
    # RE-PINNED 2026-09-07 in a joint round Sibling-C proposed and this repo
    # authored, so THIS repo carries the red window. Only the docstring's
    # opening paragraph moved: it named a pair of siblings in plain text one
    # line above the sentence forbidding exactly that, and every carrier of
    # either module is a published repo. Carriers copy the new bytes
    # BYTE-WISE and re-hash from their own disk; a digest quoted in a note is
    # not acceptance. Every tree in THAT round had hashed 629c3d51 before it.
    #
    # RE-PINNED 2026-09-20 in round B. LW proposed the round AND AUTHORED the
    # bytes, so LW carries the red window; this repo confirmed the digest off
    # the authored file and copied it BYTE-WISE with shutil.copyfile, then
    # re-hashed from its OWN disk. `winmutex.py` moved from
    # 0b112a4f6bfa88cf5f537f8869225c1821ebfe97428b1e899979797ddd71a61e, 6190
    # bytes, to the digest below at 6184 bytes. ONE COMMENT LINE moved and NO
    # BEHAVIOUR: the line named a sibling by channel code inside a file every
    # carrier holds, which is the same defect class the 2026-09-07 round
    # closed. Carriers re-hash from their own disk; a digest quoted in a note
    # is not acceptance. `slots.py` did not move in this round.
    "slots.py": "71fa2a683f2eaa04dd61feb2bebc646b5f9086e692c5acc05a9239de49d07d1b",
    "winmutex.py": "df0a7a40c28818130dfde25144c971c06060b4645e5eb5f679fbdaf55e2e08d7",
}

# ---------------------------------------------------------------------------
# 1a. The populations - FOUR of them, and no two are the same set
# ---------------------------------------------------------------------------
#
# NEVER CITE A CARRIER NUMERAL WITHOUT NAMING THE POPULATION IT COUNTS, AND
# NEVER SCOPE A SAMENESS CLAIM TO THE ops/loop DIRECTORY. Measured across all
# six fleet roots on 2026-09-20 with sha256, and every figure below is from
# that run rather than from anyone's hand-off note:
#
#   ops/loop/slots.py      FOUR carriers, all agreeing at 71fa2a68, 9627 bytes:
#                          LW, RC, RSC, SS. LL holds no copy. CS DOES HOLD the
#                          file and is still NOT in that tuple, which is the
#                          one row here that needs its mechanism spelled out.
#                          Measured this run: CS's own copy of that module is
#                          on its disk at 9627 bytes and 71fa2a68, the same
#                          bytes this pin names, but `git ls-files` over that
#                          directory in CS does not list it and
#                          `git check-ignore -v ops/loop/slots.py` there exits
#                          1 with no output - untracked AND not ignored. THE
#                          MECHANISM: this tuple counts PIN carriers, and the
#                          pin is on TRACKED bytes. An untracked file is
#                          outside every `git ls-files` corpus by construction,
#                          so no guard in CS reaches it and no joint round can
#                          re-pin it there. CS is a DISK HOLDER of that module
#                          and not a pin carrier. Same shape as LL's CHANNEL.md
#                          below, which is on LL's disk but under a vendoring
#                          prefix instead of the pinned path. If CS ever tracks
#                          it, CS joins the tuple in that same round - and the
#                          rule-C expectation in tests/test_carrier_population
#                          _prose.py moves with it, because that arm pins this
#                          tuple's LENGTH.
#   ops/loop/winmutex.py   FIVE carriers, and this round opened a window in
#                          which they do not agree. RSC alone is at the newly
#                          pinned df0a7a40, 6184 bytes, having landed round B.
#                          LW, RC and SS still hold the superseded 0b112a4f at
#                          6190 bytes - LW authored the new bytes and has not
#                          yet landed them in its own tree. CS holds a
#                          DIVERGENT 7724-byte file at e0d3ac7d, which is a
#                          different file rather than a lagging copy of this
#                          one. LL holds no copy. See WINMUTEX_DIVERGENT.
#   docs/CHANNEL.md        FIVE carriers: CS, LL, LW, RC, RSC - SS holds none.
#                          LW, RC, RSC and LL agree at fc22e86e, 25425 bytes
#                          (LL's copy sits under a third_party vendoring
#                          prefix, not at docs/CHANNEL.md); CS is still at the
#                          v1 899f6eb9, 20633 bytes.
#   the LANE WIDTH         FOUR declarers, all at 3: LW and RC and SS in
#                          ops/loop/config.json, RSC in core/config.py, listed
#                          in LANE_WIDTH_DECLARERS below. This is
#                          a FOURTH population and the one this file used to
#                          give two different sizes eight lines apart. CS holds
#                          an ops/loop/config.json that declares NO lane width
#                          at all, so it carries the file and is not a declarer;
#                          LL has no such file. A WIDTH IS NOT A PARTICIPANT
#                          COUNT. The width is 3 and the declarers are 4, and
#                          they were equal once, which is how they got conflated.
#
# THIS IS WHY A DIRECTORY-WIDE SENTENCE IS THE BUG. A sentence of the form
# <the directory> is the same everywhere across <N> trees is FALSE AT EVERY N:
# its binding condition is the four-tree slots.py set while its wording reaches
# a directory whose other module has a fifth, divergent carrier. The exception sets do not nest - CS is out of
# slots.py and in winmutex.py, LL is out of both and in CHANNEL.md, SS is in
# both modules and out of CHANNEL.md - which is why no one of these numbers ever
# corrected another and the four-versus-five dispute survived as a dispute.
#
# WHAT THESE CONSTANTS DO AND DO NOT BUY. They stop a numeral and its names
# drifting apart in the assertion messages below, which interpolate the phrases
# rather than retyping either. They are NOT mechanically tied to anything: the
# codename map is the GITIGNORED `ops/moon_sync_repos.json` and no guard may
# read it, and no tree reads another tree's disk from a test. A carrier joining
# or diverging is still a hand edit here, the same hand-maintained-literal shape
# that `tests/test_channel_doc_pin.py`'s roster numeral is filed against. Do not
# read a mechanical tie into them.

#: PIN carriers of `ops/loop/slots.py` - the trees where git STORES that file,
#: which is the only population a sha256 pin can act on. All four agree at the
#: digest pinned above. CS holds the same bytes on disk and git does not store
#: them there, so CS is a disk holder and stays out of this tuple; the
#: measurement and the mechanism are in the population block above.
SLOTS_CARRIERS: tuple[str, ...] = ("LW", "RC", "RSC", "SS")

#: Carriers of `ops/loop/winmutex.py` - a DIFFERENT and larger set.
WINMUTEX_CARRIERS: tuple[str, ...] = ("CS", "LW", "RC", "RSC", "SS")

#: The winmutex.py carriers whose bytes do NOT match the digest pinned above.
#: Measured this run by hashing each root's own disk, not predicted.
#:
#: THIS IS A ROUND WINDOW, NOT PERMANENT DRIFT, and the two must not be read
#: the same way. Round B moved this repo's pin to df0a7a40 on bytes LW
#: authored; LW, RC and SS still hold the superseded 0b112a4f, so they became
#: divergent AGAINST THE PIN the moment it moved and not by any act of their
#: own. A name leaves this tuple as that carrier lands the same bytes, and the
#: window closes when the last one does. CS is the exception that does not
#: close this way: its winmutex.py is a DIFFERENT FILE at e0d3ac7d, 7724
#: bytes, divergent before this round and unaffected by it.
WINMUTEX_DIVERGENT: tuple[str, ...] = ("CS", "LW", "RC", "SS")

#: Trees that DECLARE a lane width. A fourth population, and not a carrier set:
#: CS carries `ops/loop/config.json` and declares no width in it, so it is a
#: carrier of that file and not a declarer. The measured values are all 3, which
#: is `EXPECTED_LANES`. Do not restate that 3 as a participant count.
LANE_WIDTH_DECLARERS: tuple[str, ...] = ("LW", "RC", "RSC", "SS")

#: This tree's own code, as the four populations above claim it. Used by a
#: PREDICATE below, which is the only reason any of these tuples is more than a
#: comment. See that test for exactly how much it can and cannot catch.
THIS_TREE = "RSC"

#: Per-module phrases. Keyed by module so no message can make a claim about the
#: directory, which is the one claim that is false however it is counted.
CARRIERS_BY_MODULE = {
    "slots.py": (
        f"the {len(SLOTS_CARRIERS)} slots.py carriers "
        f"({', '.join(SLOTS_CARRIERS)}), which all agree"
    ),
    "winmutex.py": (
        f"the {len(WINMUTEX_CARRIERS)} winmutex.py carriers "
        f"({', '.join(WINMUTEX_CARRIERS)}) - a DIFFERENT set from slots.py's, "
        f"and {', '.join(WINMUTEX_DIVERGENT)} do not match the pinned digest "
        "today - see WINMUTEX_DIVERGENT for which of those is a round window "
        "and which is a different file"
    ),
}


def test_the_vendored_governor_is_present():
    """Absence must be RED, never a skip.

    Every other guard in this file is downstream of these two files existing.
    If a missing vendor drop were allowed to skip, deleting the vendor drop
    would take the entire parity contract green-and-silent, which is precisely the
    renamed-directory failure described in the module docstring.
    """
    missing = [name for name in sorted(VENDORED_MODULES) if not (LOOP_DIR / name).is_file()]
    assert not missing, (
        f"{missing} absent from {LOOP_DIR}. This repo has JOINED a machine-wide "
        "concurrency bucket shared with Sibling-E and Sibling-C, both of "
        "which acquire against it for real - and so does this repo, from run_daemon in "
        "headless/runner.py since 1a6d8da. So losing these files breaks a RUNNING LOOP "
        "here as well as silently dropping this repo out of the parity contract. "
        "Re-vendor them byte-wise "
        "from a sibling tree - do not re-author them, and do not delete this test.\n"
        "Resolve the sibling codenames in the gitignored ops/moon_sync_repos.json, "
        "and coordinate the round through moon_sync_inbox/."
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
    close together. `VENDORED_MODULES` is the independent second witness;
    Sibling-C's mirror test has always carried its own literal list for exactly
    this reason, and the port to this tree dropped it.
    """
    assert sorted(SHARED_SHA256) == sorted(VENDORED_MODULES), (
        f"SHARED_SHA256 covers {sorted(SHARED_SHA256)} but the vendored set is "
        f"{sorted(VENDORED_MODULES)}. Do not resolve this by editing whichever side "
        "is convenient: removing a digest disarms both the presence and the byte "
        "guard for that file. A module joins or leaves this set only in a joint "
        f"round with every carrier OF THAT MODULE - {CARRIERS_BY_MODULE['slots.py']}, "
        f"and {CARRIERS_BY_MODULE['winmutex.py']}. Resolve the codenames in the "
        "gitignored ops/moon_sync_repos.json and coordinate through moon_sync_inbox/."
    )
    on_disk = sorted(path.name for path in LOOP_DIR.glob("*.py"))
    assert on_disk == sorted(VENDORED_MODULES), (
        f"{LOOP_DIR} holds {on_disk}, expected {sorted(VENDORED_MODULES)}. Each module "
        "here mirrors its OWN set of sibling trees - the directory as a whole mirrors "
        "nothing, see CARRIERS_BY_MODULE - so an EXTRA file "
        "here is drift even when every pinned digest still matches - including an "
        "__init__.py, which would also change how the modules import."
    )


def test_this_tree_s_own_membership_matches_this_tree_s_own_disk():
    """The PREDICATE that stops the population tuples being decorative.

    WHY THIS ARM EXISTS. An adversarial pass established that every reference to
    `SLOTS_CARRIERS`, `WINMUTEX_CARRIERS` and `CARRIERS_BY_MODULE` was a
    docstring, a comment, or the `msg` operand of an `assert` - never a
    predicate. A tuple no predicate reads is a comment with a colon in it, and
    the failure it lets through is not cosmetic: when the digest arm finally
    fires it prints the re-pinning procedure, so a stale tuple tells a
    maintainer to run a joint round that EXCLUDES A REAL CARRIER.

    WHAT IT CHECKS, all of it from THIS tree's own disk:

      1. `CARRIERS_BY_MODULE` covers exactly `VENDORED_MODULES`. This is the
         sharpest arm here. The digest arm indexes that dict INSIDE its own
         assertion message, so a module joining the vendor drop without a phrase
         replaces the one diagnostic that matters with a KeyError traceback, at
         the exact moment somebody needs to read it.
      2. This tree's membership in each module's carrier tuple agrees with
         whether the module is on this disk.
      3. This tree is not listed as DIVERGENT for a module whose pinned digest
         this suite also asserts it matches - two arms that cannot both be right.
      4. This tree declares a lane width if and only if it claims to.

    WHAT IT STRUCTURALLY CANNOT CATCH, and this is most of it. Every row about
    ANOTHER tree is unguarded, because no test here may read a foreign disk -
    the module docstring records what a cross-tree read cost the last time it
    was tried. So CS adopting `slots.py`, LL vendoring either module, SS
    dropping one, or CS's divergent `winmutex.py` converging would all leave
    these tuples stale and every arm here green. Those rows are hand-maintained
    against a measurement taken once, and the only thing that refreshes them is
    a human re-running the six-root hash. Do not read this arm as parity.
    """
    assert sorted(CARRIERS_BY_MODULE) == sorted(VENDORED_MODULES), (
        f"CARRIERS_BY_MODULE describes {sorted(CARRIERS_BY_MODULE)} but the vendored set "
        f"is {sorted(VENDORED_MODULES)}. The digest arm indexes this dict inside its own "
        "assertion message, so a module missing here turns that arm's diagnostic into a "
        "KeyError at the moment it fires. Add the module's carrier population, measured "
        "from disk, rather than deleting the arm that noticed."
    )

    carriers_of = {"slots.py": SLOTS_CARRIERS, "winmutex.py": WINMUTEX_CARRIERS}
    for name in sorted(VENDORED_MODULES):
        present = (LOOP_DIR / name).is_file()
        claimed = THIS_TREE in carriers_of[name]
        assert present == claimed, (
            f"{name}: this tree is {'listed' if claimed else 'NOT listed'} in its carrier "
            f"tuple but the file is {'present' if present else 'ABSENT'} at {LOOP_DIR}. "
            f"One of the two is wrong. Fix the side that disagrees with disk - and if the "
            f"file genuinely left this tree, {THIS_TREE} leaves that tuple in the same "
            "edit, which is a joint round, not a local one."
        )

    assert THIS_TREE not in WINMUTEX_DIVERGENT, (
        f"{THIS_TREE} is listed as carrying a DIVERGENT winmutex.py, but this suite also "
        "asserts this tree's copy matches the pinned digest. Both cannot hold. If this "
        "tree really has diverged, the digest arm is the one that must go red first."
    )

    declares = hasattr(core_config, "MAX_CONCURRENT_LANES")
    assert declares == (THIS_TREE in LANE_WIDTH_DECLARERS), (
        f"LANE_WIDTH_DECLARERS {'includes' if THIS_TREE in LANE_WIDTH_DECLARERS else 'omits'} "
        f"{THIS_TREE}, but core.config "
        f"{'declares' if declares else 'does not declare'} MAX_CONCURRENT_LANES. Declaring a "
        "width is what makes a tree a declarer; carrying ops/loop/ is not, and CS is the "
        "measured example of the difference."
    )


@pytest.mark.parametrize("name", sorted(SHARED_SHA256))
def test_vendored_module_matches_the_pinned_cross_repo_digest(name: str):
    """Parity provable from ONE checkout, with no sibling tree on the machine."""
    path = LOOP_DIR / name
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = SHARED_SHA256[name]
    assert actual == expected, (
        f"{name} no longer hashes to the digest this repo agreed with Sibling-E "
        f"and Sibling-C. Those are codenames, and they resolve in the gitignored "
        f"ops/moon_sync_repos.json - the round is coordinated through moon_sync_inbox/.\n"
        f"  expected {expected}\n"
        f"  actual   {actual}\n"
        f"  file     {path}\n"
        "\n"
        f"{name} is BYTE-IDENTICAL-BY-CONTRACT across {CARRIERS_BY_MODULE[name]}. Scope "
        "this to the FILE and never to the ops/loop directory: the two modules have "
        "DIFFERENT carrier sets and a directory-wide claim is false at every count. "
        "They coordinate "
        "through this file's on-disk protocol against ONE shared bucket, so a divergence "
        "is not a merge conflict anybody sees - it is a silent concurrency bug.\n"
        "\n"
        "DO NOT re-hash the local file to make this green. A local regeneration launders "
        "a unilateral drift into 'agreed' and turns this guard into a rubber stamp. "
        f"RE-PINNING IS A JOINT ACT across {CARRIERS_BY_MODULE[name]}, in ONE round: "
        "agree the new bytes; "
        "copy them BYTE-WISE into every tree (a text write CRLF-mangles them on Windows "
        "and this pin is on bytes); re-hash from EACH tree's OWN disk rather than "
        "trusting the digest in anyone's hand-off note; confirm EVERY carrier agrees; then "
        "update this dict and its counterpart in every other carrier tree in the same round."
    )


def _carriage_return_offsets(data: bytes) -> list[int]:
    """Byte offsets of every 0x0D in `data`.

    ANY 0x0D, not just the CRLF pair. `tests/test_line_endings.py` counts
    `b"\\r\\n"`, so a LONE CR - which a botched normalisation produces, and which
    changes the digest exactly as much - is invisible there and visible here.
    """
    return [i for i, byte in enumerate(data) if byte == 0x0D]


@pytest.mark.parametrize("name", sorted(SHARED_SHA256))
def test_vendored_module_carries_no_carriage_return(name: str):
    """Names the ONE cause that makes the digest arm above unreadable.

    The pin is on BYTES. A TEXT-mode copy of a shared file on Windows rewrites
    every LF to CRLF, producing a file that READS identically to the sibling's,
    diffs identically, and hashes DIFFERENTLY. Without this arm that presents as
    an unexplained digest mismatch, and the first response to an unexplained
    mismatch is to re-hash locally - which the digest arm's own message forbids,
    because it launders a mangled copy into "agreed".

    WHY THE EXISTING COVERAGE DOES NOT REACH THIS, measured 2026-09-20.

      * `tools/precommit_gate.py` scans these files - they are tracked, and
        `--scan-files` on the pair reports `selected=2 scanned=2 exempt=0` - but
        its predicate is `ord(c) > 127` at :267 and CR is 0x0D. It also reads
        STAGED content, which `.gitattributes` has already normalised to LF.
      * `.gitattributes` forces `eol=lf` for `.py`, which is precisely what HIDES
        a working-tree CRLF from every diff rather than preventing it.
      * `tests/test_line_endings.py` does sweep these two files - `git check-attr
        eol` answers `lf` for both - but it derives its corpus from `git
        ls-files` and SKIPS when git is unusable, so a git-less checkout loses
        that coverage while this digest arm still fires. It also counts the CRLF
        PAIR only. This arm is git-independent and inherits its file list from
        `SHARED_SHA256`, the same source the digest arm parametrizes over, so a
        module joining the vendor drop joins this guard in the same edit.

    NO NON-ASCII ARM HERE, DELIBERATELY. That byte class is already caught twice
    - at commit time by the glyph gate and in the CI drift sweep - and unlike a
    CR it is VISIBLE: it shows in the diff and the gate reports it as file:line.
    A CR earns a named arm because the ordinary diagnostics are blind to it; a
    third copy of the ASCII predicate would only suggest this file owns it.
    """
    path = LOOP_DIR / name
    offsets = _carriage_return_offsets(path.read_bytes())
    assert not offsets, (
        f"{path} carries {len(offsets)} carriage-return byte(s), first at offset "
        f"{offsets[0] if offsets else -1}. This is almost certainly a CRLF WORKING-TREE "
        "COPY: the file was copied in TEXT mode from a sibling tree, so Windows rewrote "
        "every LF to CRLF. It reads identically to the sibling's copy and `git diff` "
        "shows nothing, because .gitattributes declares eol=lf and the index normalises "
        "it - but the cross-repo pin in SHARED_SHA256 is on BYTES, so the digest arm is "
        "red for a reason no diff can display.\n"
        "\n"
        "FIX: re-copy from the sibling tree in BINARY mode - `copy /b`, `shutil.copyfile`, "
        "`git show <ref>:ops/loop/" + name + " > " + name + "` with a binary redirect, or "
        "`Path(dst).write_bytes(Path(src).read_bytes())`. NEVER `read_text()`/`write_text()`, "
        "which is what produced this. Do NOT re-hash the local file to make the digest arm "
        "green: that pins the mangled bytes and desynchronises every other carrier."
    )


def test_the_carriage_return_detector_actually_fires(tmp_path: Path):
    """Non-vacuity, against the REAL bytes, without touching the real files.

    Each vendored module is byte-identical-by-contract across ITS OWN carriers,
    never the whole directory across one set, and both are frozen here, so
    the mutation happens on a tmp_path COPY. Both arms are needed: the
    first proves the detector can go red, the second proves it is not simply
    red on everything - a detector that fires on the untouched bytes too would
    score full marks on the first arm and guard nothing.
    """
    source = LOOP_DIR / sorted(SHARED_SHA256)[0]
    original = source.read_bytes()
    assert b"\n" in original, "the sample has no LF to mangle, so the control proves nothing"

    clean = tmp_path / "clean.py"
    clean.write_bytes(original)
    assert _carriage_return_offsets(clean.read_bytes()) == [], (
        "the survivor arm: a byte-wise copy of the real file must stay clean, or this "
        "detector is reporting on itself rather than on line endings"
    )

    mangled = tmp_path / "mangled.py"
    mangled.write_bytes(original.replace(b"\n", b"\r\n"))
    assert _carriage_return_offsets(mangled.read_bytes()), (
        "a CRLF copy of the real file was not detected; the guard above is vacuous"
    )

    # And the reason the arm above reads BYTES. `read_text` strips CR through
    # universal newlines, so a text-mode read of the mangled copy is
    # indistinguishable from the clean one - the exact blindness that would
    # make the guard pass on a file that hashes wrong.
    assert mangled.read_text(encoding="utf-8") == clean.read_text(encoding="utf-8"), (
        "universal newlines no longer hide CR; the read_bytes() above is still correct, "
        "but this comment's premise has changed and the arm should be revisited"
    )
    assert hashlib.sha256(mangled.read_bytes()).hexdigest() != SHARED_SHA256[source.name], (
        "a CRLF copy must not hash to the pinned digest; if it did, the byte pin would "
        "not be distinguishing line endings at all"
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
    cycle in any of the three MEASURED ACQUIRERS - LW, RC and this tree; a
    population distinct from every carrier set above - may be holding slots in it
    right now. A test
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
    repo is forbidden to edit unilaterally, which is a change every `SLOTS_CARRIERS`
    tree has to make - `hold()` lives in `slots.py` - not a test fix. `entered ==
    workers` is left out for the same reason: it fails outright once every slot
    has leaked.
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
    # RESTORED after an adversarial pass REFUTED this test at 690d8b7.
    # Sibling-C asserts this (its `assert not errors`); the port to this tree
    # collected `failures` and then never asserted on it, mentioning it only
    # inside another assertion's failure message - so it was load-bearing
    # nowhere. The demonstrated hole: mutate `hold()` so the deadline check
    # becomes `if deadline is not None:` and the governor stops QUEUEING
    # entirely, raising SlotTimeout on the first full pass instead of waiting.
    # Every arm above still passes, because the two holders the mutant does
    # admit satisfy both `peak == max_slots` and `entered >= max_slots`, while
    # the two starved workers land silently in `failures`. That mutant fails
    # Sibling-C's suite and passed this one: 19 passed, exit 0.
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

    A leaked lock permanently narrows a bucket the three measured acquirers draw
    from - LW, RC and this one,
    included, since `1a6d8da` put the daemon loop's live passes inside a held
    slot - and it is reclaimed only by the stale sweep, which is deliberately set
    to three cycle deadlines, so the damage outlives the run that caused it by
    hours.
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
    """Fail-open: a crashed holder must not deadlock the other two acquirers.

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

    assert removed == 0, "a live holder's lock was stolen; two acquirers now believe they hold it"
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
    hand. Sibling-C tests this; the port to this tree dropped it.
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

    The bucket is one directory the three measured acquirers share - LW, RC and
    this tree, which is not the same population as any carrier set. When it is full,
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
    exists in this tree today. If any two of `LANE_WIDTH_DECLARERS` disagree, the
    machine-wide ceiling becomes the LARGER of the values - each repo is
    correctly bounded by its own belief, and the bucket is bounded by nobody.
    """
    assert core_config.MAX_CONCURRENT_LANES == EXPECTED_LANES, (
        f"core.config.MAX_CONCURRENT_LANES is {core_config.MAX_CONCURRENT_LANES}, but the "
        f"{len(LANE_WIDTH_DECLARERS)} lane-width declarers "
        f"({', '.join(LANE_WIDTH_DECLARERS)}) all pass {EXPECTED_LANES}. Changing this is "
        f"an agreement across all {len(LANE_WIDTH_DECLARERS)} of them, not a local tuning "
        "knob: the bucket models ANTHROPIC ACCOUNT concurrency, which is ONE pool for every "
        "tree that acquires against it - SS included, which joined the bucket 2026-09-20. "
        "That population is NOT the slots.py carrier set and NOT the bucket width, both of "
        "which this file used to conflate with it. The codenames resolve in the "
        "gitignored ops/moon_sync_repos.json; the round runs through moon_sync_inbox/."
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
        f"{core_config.MAX_CONCURRENT_LANES!r}, and the width agreed with Sibling-C and "
        f"Sibling-E is {EXPECTED_LANES!r}. All three must be the same number: two "
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
    Sibling-C drives its loop from exactly such a file surface, and if that
    surface is ever ported here the lane width would arrive in JSON - a second
    place for the number to live, and the first place it would drift.

    DELIBERATELY NO `assert found`. Sibling-C's copy has that arm because
    that sibling has the files; asserting non-emptiness here would be red on
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
