#!/usr/bin/env python
"""Report which `moon_sync_inbox/` notes and drops this repo has not read yet.

WHY A SCRIPT AND NOT A LIVE WATCHER. A session-scoped watcher dies with its
session. `moon_sync_inbox/` is gitignored on purpose - a note is correspondence,
not source - so a cold session inherits no record of what it already answered,
and an overnight note looks exactly like one dealt with hours ago. The failure
that costs real time is not a missed note; it is a note answered TWICE, or a
sibling's question left sitting while every agent assumes another took it.
Sibling-C's charter states the rule: silence is not agreement.

So the durable half is a WATERMARK on disk, and this script is how a session
reads and advances it.

  python scripts/watch_inbox.py                    # what is new since the mark
  python scripts/watch_inbox.py --all              # everything, new or not
  python scripts/watch_inbox.py --mark             # record the current set read
  python scripts/watch_inbox.py --quiet-when-empty # for a per-prompt hook

READING IS NOT ACKNOWLEDGING. Listing never advances the watermark; `--mark` is
a separate, deliberate act, because "I saw it scroll past" and "I answered it"
are different states and only the second one is safe to forget. That separation
is also what stops a subagent's session start from marking the operator's queue
as read.

WHAT IS AN ENTRY, AND WHY THE KEY IS A PAIR
===========================================

Every top-level `.md` file is a NOTE and every top-level directory is a DROP,
and both are first-class entries. The watermark keys each one on the PAIR
(key, digest) rather than on its name:

  note   key `<filename>`      digest sha256 of the file's bytes
  drop   key `<dirname>/`      digest of a manifest computed over WHAT IS ON DISK

THIS FIXED FOUR MEASURED HOLES. All five repos on this cross-repo channel
independently built the same watcher and each printed a confident "nothing new"
over a real payload. Measured in a fixture inbox, 2026-09-07:

  PASS  a brand new note is unread
  PASS  marking clears it
  FAIL  a note corrected IN PLACE, same filename, does not resurface
  FAIL  a 2-file subdirectory drop does not surface at all
  FAIL  an edited subdirectory payload does not surface
  FAIL  a file swapped inside a drop, count equal, does not surface

The root cause was two lines. The walker globbed `*.md` at the top level only,
and a DIRECTORY has no `.md` suffix, so `from-RC-verbatim/` - 48 real files:
hooks, guards, tools, tests - was invisible while the notes beside it merely
described them. And the watermark keyed on the filename alone, so a note edited
under a CORRECTION heading read as already answered.

THE DROP MANIFEST, and it is computed here rather than read from the sender:

  one line per contained file: the drop-relative POSIX path, a NUL byte, then
  that file's sha256; sorted; joined with newlines; hashed once.

The relative path inside each line is what makes two files SWAPPING CONTENTS
move the digest - the multiset of hashes is unchanged but the pairing is not.
An unreadable file contributes its exception CLASS in place of a hash, so it
moves the digest rather than vanishing from the manifest; a file that silently
drops out is a payload reported as unchanged while it is not.

TWO OTHER KEY SHAPES WERE PROPOSED ACROSS THE FLEET AND BOTH ARE REFUTED. Do
not re-derive them:

  FILE COUNT is refuted. A sender who REPLACES a file leaves the count equal,
  so the drop reads as already acknowledged. `test_two_files_swapping_contents_
  inside_a_drop_re_surfaces_it` pins it, and asserts the count did NOT move so
  the arm cannot pass under a count-keyed watcher.

  A DIGEST OF THE SENDER'S `MANIFEST.sha256` is refuted. Sibling-C
  measured a payload edited without regenerating its manifest: same manifest,
  completely different contents, same key, silently unread. Keying on a
  sender's manifest means trusting the sender remembered to rebuild it, which
  is precisely the assumption a watcher exists to remove. It is SHIPPED as
  human context when present and is never the key.

AN EMPTY DROP IS STILL REPORTED. A drop is an entry because of its NAME, never
because it has content to hash. That is the fleet's standing one-line test: put
an empty directory in the inbox and see whether the next report mentions it.

A RENAME STILL RESURFACES, and that is the accepted cost, unchanged.
Sibling-C measured it 2026-09-07: Sibling-A re-dated four notes and every
seen-name watcher on the box reported four unread notes already answered. A
false "new mail" costs one glance; a missed correction costs whatever the
correction was for.

BACKWARD COMPATIBILITY WITH THE SHIPPED NAME-ONLY WATERMARK
===========================================================

The watermark that shipped held `{"seen": [<name string>, ...]}` - names only,
80-odd of them on this machine. Discarding that on a version bump would dump
the entire inbox back on the operator as unread, which is worse than the bug it
fixes, so a legacy entry GRANDFATHERS its note: a name in the old list counts
as read whatever the file now hashes to, until the next `--mark` rewrites the
state in the keyed shape.

A legacy watermark never held a DIRECTORY, because the old walker could not see
one, so every drop surfaces on the first run after this change. That is the fix
arriving, not a regression.

The reader dispatches on the TYPE of `seen` - a list is legacy, an object is
current - rather than on the `version` field. A version integer is a claim a
writer makes about a payload; the shape is the payload. `version` is written
for a human reading the file.

DEGRADES TOWARD RE-REPORTING. A missing inbox is normal in a fresh clone and is
reported as a plain line, not a traceback. A corrupt watermark is treated as if
nothing had been read, which re-reports notes rather than dropping them: a
duplicate read costs a minute, a dropped note costs a sibling waiting on an
answer nobody knows they owe. No raw exception string ever reaches the report.

The watermark lives under `ops/runtime/`, which is gitignored, and is written
through `core/atomic_io.py` - the only sanctioned state-write path in this tree,
because readers poll mid-write.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
from pathlib import Path
from typing import NamedTuple

#: Present on Windows only. Named here so the walk reads the same on every
#: platform and the Windows-only bit is a lookup rather than a branch.
_FILE_ATTRIBUTE_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.atomic_io import atomic_write_json, read_json  # noqa: E402

#: Correspondence lives here. Gitignored: see `moon_sync_inbox/README.md`.
DEFAULT_INBOX = REPO_ROOT / "moon_sync_inbox"

#: Runtime state, gitignored, never source.
DEFAULT_STATE = REPO_ROOT / "ops" / "runtime" / "inbox_seen.json"

#: What has been SHOWN, which is a different fact from what has been READ. Kept
#: in its own file so a plain reporting run leaves the WATERMARK byte-unchanged
#: and mtime-unmoved - the property that stops a subagent's session start from
#: consuming the operator's queue.
DEFAULT_REPORTED = REPO_ROOT / "ops" / "runtime" / "inbox_reported.json"

#: This repo's own code in the `from-<CODE>-` naming convention. A note we sent
#: sits in the same directory as one we received, so direction is read off the
#: filename rather than guessed from mtime.
SELF_CODE = "RSC"

#: Written into the watermark for a human. The READER dispatches on the shape
#: of `seen`, not on this number - see the module docstring.
STATE_VERSION = 2

#: A sender's own checksum listing. Surfaced as human context; never the key.
MANIFEST_NAME = "MANIFEST.sha256"

#: Streamed rather than slurped: a drop can carry an arbitrary payload and this
#: runs on a hook with a five second ceiling.
_CHUNK_BYTES = 1 << 20

#: Prefix for the stand-in a file contributes when it cannot be read. It is a
#: digest INPUT, never printed on a user-facing surface.
_UNREADABLE = "unreadable:"

#: Ceiling on entries visited while walking ONE drop. The count is the harmless
#: half of the junction defect; the walk running past the hook's timeout is the
#: outage, because a killed hook surfaces nothing at all. A drop that blows this
#: stops walking and says so rather than reporting a partial payload as whole.
MAX_DROP_ENTRIES = 2000

#: Why an entry could not be digested. These are digest INPUTS and they are also
#: printed - an anomaly is the one thing that must reach the report every run,
#: so its reason is written to be read. They carry no bytes of any payload.
REASON_REPARSE = "reparse-point-not-followed"
REASON_UNCLASSIFIABLE = "neither-file-nor-directory"
REASON_UNWALKABLE = "directory-could-not-be-listed"
REASON_BUDGET = "entry-budget-exhausted"


class Entry(NamedTuple):
    """One thing in the inbox, note or drop, with what it currently hashes to.

    `files` and `manifest` are appended at the END with defaults, per the
    convention in `CLAUDE.md`: a mid-tuple required field breaks every existing
    positional construction and its tests.
    """

    key: str
    digest: str
    path: Path
    kind: str
    files: int = 0
    manifest: bool = False
    anomalies: tuple[str, ...] = ()


def direction(name: str) -> str:
    """`sent` if this repo wrote the note, `recv` otherwise.

    Outbound notes are LABELLED rather than hidden. A cold session wants to know
    what this repo said as well as what arrived - half a conversation reads as
    an unanswered question.
    """
    return "sent" if f"-from-{SELF_CODE}-" in name else "recv"


def _file_digest(path: Path) -> str:
    """sha256 of a file's bytes, or a marker naming why it could not be read.

    The marker is deliberate. A file that failed to open must MOVE the digest
    it contributes to, not disappear from it - a payload half of which vanished
    from the manifest would otherwise report as unchanged.
    """
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(_CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        return f"{_UNREADABLE}{exc.__class__.__name__}"
    return digest.hexdigest()


def _classify(child) -> tuple[str, str]:  # noqa: ANN001 - duck-typed on purpose
    """(`dir` | `file` | `anomaly`, reason). The reason is empty unless anomalous.

    THIS EXISTS BECAUSE OF THE MISSING `else`. An `if is_dir() / elif is_file()`
    ladder drops any entry BOTH calls answer False for off the end of the loop,
    under a confident exit 0. Sibling-C reached that state with a trailing dot
    or space in a filename; Sibling-D could not create such a name on its box at
    all, so the class is handled here rather than tested through a trick that
    does not port. An unstattable entry lands here too, by the same argument: it
    must be reported, never assumed away.
    """
    try:
        if child.is_dir():
            return "dir", ""
        if child.is_file():
            return "file", ""
    except OSError:
        return "anomaly", REASON_UNCLASSIFIABLE
    return "anomaly", REASON_UNCLASSIFIABLE


def _is_reparse_point(path: Path) -> bool:
    """Whether `path` is a link, junction or any other reparse point.

    `Path.is_symlink()` IS NOT ENOUGH ON WINDOWS. It returns False for an NTFS
    junction, which is why `rglob` descends one: Sibling-D measured a one-file
    drop reported as 32 files, Sibling-A measured the same shape at 6, and a
    junction over a large tree runs the walk past the hook's timeout. The
    attribute bit is the check that actually answers the question; the
    `is_symlink` half is the portable fallback for everything else.
    """
    try:
        if path.is_symlink():
            return True
        attrs = getattr(os.lstat(path), "st_file_attributes", 0)
    except (OSError, ValueError):
        # Unstattable is not "ordinary". Treating it as a reparse point prunes
        # the walk, and the caller records it as an anomaly either way.
        return True
    return bool(attrs & _FILE_ATTRIBUTE_REPARSE_POINT)


def _walk_drop(drop: Path) -> tuple[list[Path], list[tuple[str, str]]]:
    """(files under `drop` in a stable order, (relative path, reason) anomalies).

    ITERATIVE AND PRUNED, because `rglob` cannot be told not to follow a
    junction. Every entry the walk refuses to digest - a reparse point, an
    unlistable directory, something that is neither a file nor a directory, or
    the point at which the budget ran out - comes back as an anomaly rather
    than as silence. That is Sibling-C's rule: WHAT CANNOT BE DIGESTED IS
    FORCED INTO EVERY REPORT WITH ITS REASON, never keyed silently and never
    dropped.
    """
    files: list[Path] = []
    anomalies: list[tuple[str, str]] = []
    pending = [drop]
    visited = 0

    def rel_of(path: Path) -> str:
        try:
            return path.relative_to(drop).as_posix()
        except ValueError:
            return path.name

    while pending:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError:
            anomalies.append((rel_of(current), REASON_UNWALKABLE))
            continue
        for child in children:
            visited += 1
            if visited > MAX_DROP_ENTRIES:
                anomalies.append((rel_of(child), REASON_BUDGET))
                pending.clear()
                break
            if _is_reparse_point(child):
                # NOT descended and NOT ignored. Both halves are the fix.
                anomalies.append((rel_of(child), REASON_REPARSE))
                continue
            kind, reason = _classify(child)
            if kind == "dir":
                pending.append(child)
            elif kind == "file":
                files.append(child)
            else:
                anomalies.append((rel_of(child), reason))

    files.sort(key=lambda p: p.as_posix())
    anomalies.sort()
    return files, anomalies


def _drop_manifest(drop: Path) -> tuple[str, int, bool, tuple[str, ...]]:
    """(manifest digest, file count, sender manifest present, anomaly reasons).

    Computed over WHAT IS ON DISK. See the module docstring for why a sender's
    own `MANIFEST.sha256` is refuted as the key and shipped as context instead.

    THE FORMAT DOES NOT MOVE FOR A DROP OF ORDINARY FILES. An anomaly
    contributes a line of exactly the same shape - relative path, NUL, then its
    reason where a hash would be - so a drop with no anomalies hashes to the
    byte-identical value it hashed to before this walk existed. Sibling-D named
    the constraint and this repo measured the cost of breaking it at 88 notes:
    a watcher that re-reports the whole inbox because its digest format moved
    is a worse artifact than the silence it fixes.
    """
    files, anomalies = _walk_drop(drop)
    lines = []
    manifest = False
    for path in files:
        try:
            rel = path.relative_to(drop).as_posix()
        except ValueError:
            rel = path.name
        if rel == MANIFEST_NAME:
            manifest = True
        lines.append(f"{rel}\0{_file_digest(path)}")
    for rel, reason in anomalies:
        lines.append(f"{rel}\0{reason}")
    body = "\n".join(sorted(lines))
    reasons = tuple(f"{rel}: {reason}" for rel, reason in anomalies)
    return hashlib.sha256(body.encode("utf-8")).hexdigest(), len(files), manifest, reasons


def _entries(inbox: Path) -> list[Entry]:
    """Every note and drop in the inbox, oldest name first.

    An absent or unreadable inbox is empty rather than an error: a fresh clone
    has no `moon_sync_inbox/` at all.
    """
    try:
        if not inbox.is_dir():
            return []
        children = sorted(inbox.iterdir(), key=lambda p: p.name)
    except OSError:
        return []

    entries: list[Entry] = []
    for child in children:
        try:
            if _is_reparse_point(child):
                # A link at the TOP level is a deliverable nobody can digest.
                entries.append(
                    Entry(child.name, REASON_REPARSE, child, "anomaly", 0, False, (REASON_REPARSE,))
                )
                continue
            kind, reason = _classify(child)
            if kind == "dir":
                digest, count, manifest, reasons = _drop_manifest(child)
                entries.append(
                    Entry(child.name + "/", digest, child, "drop", count, manifest, reasons)
                )
            elif kind == "file" and child.name.lower().endswith(".md"):
                entries.append(Entry(child.name, _file_digest(child), child, "note"))
            elif kind == "file":
                # A LOOSE TOP-LEVEL FILE IS A DELIVERABLE IN ITS OWN RIGHT.
                # Measured on this channel 2026-09-07: Sibling-A delivered
                # `REFERENCE-moon_sync_poller.py.txt` beside a note, and every
                # watcher globbing `*.md` was silent about it - not a note, not
                # a directory, so it matched nothing. It is keyed on its content
                # like everything else and NONE of its bytes reach the report.
                entries.append(Entry(child.name, _file_digest(child), child, "file"))
            else:
                entries.append(Entry(child.name, reason, child, "anomaly", 0, False, (reason,)))
        except OSError:
            # One unreadable child must not take the whole report down, but it
            # must not vanish either - it is reported with its reason.
            entries.append(
                Entry(
                    child.name,
                    REASON_UNCLASSIFIABLE,
                    child,
                    "anomaly",
                    0,
                    False,
                    (REASON_UNCLASSIFIABLE,),
                )
            )
    return entries


def _seen(state: Path) -> tuple[dict[str, str], set[str]]:
    """(current key -> digest map, legacy name set). Corrupt state means neither.

    Exactly one of the two is ever populated, because `seen` is either an
    object or a list. Both are returned so the caller does not have to know
    which shape it got.
    """
    payload = read_json(state, default=None)
    if not isinstance(payload, dict):
        return {}, set()
    seen = payload.get("seen")
    if isinstance(seen, dict):
        return {k: v for k, v in seen.items() if isinstance(k, str) and isinstance(v, str)}, set()
    if isinstance(seen, list):
        # The shipped name-only shape. A name here grandfathers its note
        # whatever the file now hashes to - see the module docstring.
        return {}, {n for n in seen if isinstance(n, str)}
    return {}, set()


def _is_seen(entry: Entry, digests: dict[str, str], legacy: set[str]) -> bool:
    if entry.key in digests:
        return digests[entry.key] == entry.digest
    return entry.key in legacy


def survey(inbox: Path, state: Path) -> tuple[int, list[Entry]]:
    """(entries examined, entries unread). Pure read - never marks.

    RETURNS THE PAIR ON PURPOSE. A watcher that matches nothing reports
    "unread: none" and looks exactly like a clean one: zero out of zero
    rendered as a clean bill of health. The examined count is what lets a
    caller - and every arm of `tests/test_watch_inbox.py` - tell the two apart.
    """
    entries = _entries(inbox)
    digests, legacy = _seen(state)
    return len(entries), [e for e in entries if not _is_seen(e, digests, legacy)]


def unseen_entries(inbox: Path, state: Path) -> list[Entry]:
    """Notes and drops the watermark does not already hold at this digest."""
    return survey(inbox, state)[1]


def unseen_notes(inbox: Path, state: Path) -> list[Path]:
    """The unread NOTES only, as paths. Kept for callers that predate drops."""
    return [e.path for e in unseen_entries(inbox, state) if e.kind == "note"]


def mark_seen(inbox: Path, state: Path) -> bool:
    """Record every note and drop currently in `inbox` as read, at its digest.

    Returns whether the write landed.

    THE SET IS REWRITTEN FROM THE CURRENT LISTING, NOT MERGED INTO. That is
    deliberate rather than incidental: a key that no longer exists drops out,
    so a re-dated batch cannot accumulate two entries per note forever.
    Sibling-C found the same property in its own implementation by accident and
    asked that it be kept on purpose. `test_the_seen_set_does_not_accumulate_
    renamed_notes` pins it.

    Rewriting is also the migration: one `--mark` carries a legacy name-only
    watermark over to the keyed shape.
    """
    state.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": STATE_VERSION,
        "seen": {entry.key: entry.digest for entry in _entries(inbox)},
    }
    return atomic_write_json(state, payload)


def read_reported(reported: Path) -> set[str]:
    """The keys this repo has ever SHOWN the operator. Corrupt means empty.

    THIS RECORD NEVER FEEDS THE UNREAD DECISION. It is written by a plain
    reporting run, so if it ever reached `_is_seen` a session start would
    silently consume the operator's queue - which is exactly the defect `--mark`
    is separated out to prevent, re-entering behind it. Its only reader is
    `withdrawn`. `test_the_report_record_is_never_a_second_acknowledgement_path`
    pins that, and it is the arm nobody asks for.
    """
    payload = read_json(reported, default=None)
    if not isinstance(payload, dict):
        return set()
    shown = payload.get("reported")
    if not isinstance(shown, list):
        return set()
    return {k for k in shown if isinstance(k, str)}


def record_reported(reported: Path, keys: list[str]) -> bool:
    """Add `keys` to the record of what has been shown. Union, never a rewrite."""
    merged = read_reported(reported) | set(keys)
    reported.parent.mkdir(parents=True, exist_ok=True)
    return atomic_write_json(reported, {"version": 1, "reported": sorted(merged)})


def withdrawn(inbox: Path, state: Path, reported: Path) -> list[str]:
    """Keys this repo has seen or shown that are no longer in the inbox.

    THE BASELINE IS `reported | seen`, NOT `seen` ALONE. Sibling-D's correction,
    and the case that motivated the whole feature is the one a seen-only
    baseline scores as a non-event: notes LISTED at session start and pulled
    before anyone ran the acknowledge live in the REPORT record only.

    THE COMPARISON IS ON THE STABLE NAME. Once keys carry a content digest an
    EDIT and a RETRACTION both move the key, so comparing digests would file an
    edited note in two contradictory sections of the same report. This tool's
    key already IS the bare name, with the digest held beside it as the value,
    so the name comparison is the natural one rather than a stripping step.

    WHY IT IS CARRIED RATHER THAN REPORTED ONCE. Reporting a withdrawal exactly
    once puts it straight back into the watermark's own failure class - a
    session cleared before anyone reads the output loses it - and unlike every
    other inbox event there is no artifact left on disk to notice later. It is
    carried until an explicit `--mark` prunes it.
    """
    digests, legacy = _seen(state)
    baseline = set(digests) | legacy | read_reported(reported)
    return sorted(baseline - {entry.key for entry in _entries(inbox)})


def prune_records(inbox: Path, reported: Path) -> bool:
    """Drop every reported key that is no longer in the inbox.

    THE ACKNOWLEDGE HAS TO PRUNE BOTH RECORDS. Sibling-D shipped this half
    broken and found it twenty minutes later by running its own command against
    live mail: the acknowledge pruned the SEEN record and never touched the
    REPORT record, so a withdrawn name re-derived itself on every run and could
    never be cleared by anything. Every arm passed, because every arm asserted
    that a withdrawal REPORTS and none asserted that it STOPS. A report the
    reader cannot clear is a defect even when every line in it is true.
    """
    present = {entry.key for entry in _entries(inbox)}
    reported.parent.mkdir(parents=True, exist_ok=True)
    keep = sorted(read_reported(reported) & present)
    return atomic_write_json(reported, {"version": 1, "reported": keep})


def _describe(entry: Entry) -> str:
    """The human-context suffix on a drop's line. Empty for a note."""
    bits: list[str] = []
    if entry.kind == "drop":
        bits.append(f"{entry.files} file" + ("" if entry.files == 1 else "s"))
        if entry.manifest:
            bits.append(f"{MANIFEST_NAME} present, not used as the key")
    elif entry.kind == "file":
        bits.append("loose file, not a note")
    # AN ANOMALY IS FORCED INTO EVERY REPORT WITH ITS REASON. It is the one
    # thing that must never be summarised away: the entry the walk could not
    # digest is precisely the one the old walker was silent about.
    bits.extend(entry.anomalies)
    if not bits:
        return ""
    return "  (" + ", ".join(bits) + ")"


def _render(entries: list[Entry], heading: str) -> None:
    if not entries:
        print(f"{heading}: none")
        return
    print(f"{heading}: {len(entries)}")
    for entry in entries:
        print(f"  [{direction(entry.key)}] {entry.key}{_describe(entry)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report unread moon_sync_inbox notes and advance the watermark.",
    )
    parser.add_argument("--dir", default=str(DEFAULT_INBOX), help="inbox directory")
    parser.add_argument("--state", default=str(DEFAULT_STATE), help="watermark file")
    parser.add_argument("--all", action="store_true", help="list every note, read or not")
    parser.add_argument("--reported", default=str(DEFAULT_REPORTED), help="report record")
    parser.add_argument("--mark", action="store_true", help="record the current set as read")
    parser.add_argument(
        "--quiet-when-empty",
        action="store_true",
        help="print nothing at all when there is nothing to report",
    )
    args = parser.parse_args(argv)

    inbox = Path(args.dir)
    state = Path(args.state)
    reported = Path(args.reported)

    if not inbox.is_dir():
        # Normal in a fresh clone. The directory is gitignored, so it does not
        # arrive with the repository.
        if not args.quiet_when_empty:
            print(f"no inbox at {inbox} - nothing to report")
        return 0

    if args.all:
        entries, heading = _entries(inbox), "all notes"
    else:
        entries, heading = unseen_entries(inbox, state), "unread"

    # QUIET IS FOR THE PER-PROMPT HOOK. It runs on every single prompt, and a
    # hook that speaks when it has nothing to say trains the reader to skip it -
    # at which point it is worse than absent, because it looks wired.
    gone = withdrawn(inbox, state, reported)

    if entries or gone or not args.quiet_when_empty:
        _render(entries, heading)

    # A WITHDRAWAL IS FILED AS AN ANOMALY, NOT AS AN INFORMATIONAL LINE.
    # Sibling-A pulled 50 files from four inboxes in one night and every
    # arrival-keyed watcher on this box reported silence while an entire payload
    # left the channel; two senders then spent a night reasoning about bytes the
    # receiver did not have. It is the only inbox event with no artifact left on
    # disk, so the watcher is the only thing that can say it happened.
    if gone:
        print(f"WITHDRAWN after being shown: {len(gone)}")
        for key in gone:
            print(f"  [gone] {key}")
        print("  (run --mark to acknowledge; they are carried until you do)")

    # Recorded AFTER rendering, so the record is of what was actually shown.
    # This never touches the watermark and never feeds the unread decision.
    if entries:
        record_reported(reported, [entry.key for entry in entries])

    if args.mark:
        if mark_seen(inbox, state) and prune_records(inbox, reported):
            print(f"marked read: {state}")
        else:
            print("could not update the watermark - it stays where it was")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
