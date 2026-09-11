# ADR-010: A tracked write tracer that publishes its own blind spots

**Status:** Accepted, 2026-09-11
**Closes:** the ROADMAP row opened 2026-09-11 that is about the INSTRUMENT
rather than about any finding it produced

## Context

On 2026-09-11 this tree measured a write-isolation claim with two ad-hoc write
tracers. Neither was ever a tracked artifact. `git ls-files` matched on
`tracer` returned nothing at all, so nothing a later session could clone carried
either instrument, its coverage, or its limits. The readings survived in prose;
the thing that produced them did not survive at all.

That is the defect this ADR rules on, and it is a defect in the instrument, not
in any number it printed.

### What the ROADMAP row says, and it is the load-bearing input

The row records that neither tracer used that session sees `os.open` followed by
`os.fdopen`, because the descriptor is an int and no path ever matches. It
records that this shape is LIVE in `ops/loop/slots.py`, which writes the
machine-wide bucket the halt ruling in CLAUDE.md names by name. It records that
neither tracer patched DELETION or TRUNCATION at all, while this tree calls
`shutil.rmtree` at session finish and `unlink` in several files. And it draws
the conclusion this ADR adopts: every "0 bytes written" reading taken with
either tracer is a statement about the shapes it patched.

### What was measured here, in this worktree, on 2026-09-11

- **`ops/loop/slots.py:189` is the `os.open` call** - `os.O_CREAT | os.O_EXCL |
  os.O_WRONLY` - and **`ops/loop/slots.py:195` is the `os.fdopen` that wraps the
  returned descriptor**. A tracer that keys on a path argument sees neither: the
  path reaches `os.open` and the writes go through a file object built from an
  int.
- **EMPTY-FILE CREATION WAS INVISIBLE, and that is the concrete false negative
  this whole decision exists to prevent.** `os.open(p, O_CREAT | O_EXCL)`,
  `Path.touch()` and `open(p, "x")` each brought a file into existence and
  produced NO event, because no bytes moved. The lock file at
  `ops/loop/slots.py:189` is created by exactly that call, in exactly the
  machine-wide bucket the halt ruling names, so a "0 bytes written" reading over
  a slot acquisition would have read CLEAN while the lock files appeared on
  disk. An empty file that was not there before is a filesystem mutation. An
  instrument that answers zero bytes for it has answered a different question
  than the one asked.
- **`shutil.copy2` produced ZERO events through the unpatched module** on
  CPython 3.14.4 on Windows, because `shutil.copyfile` takes a native fast path
  that never calls `open`. Transitive coverage through `builtins.open` would
  therefore have been correct on one platform and an overstatement on this one,
  which is why the shutil copy family is patched BY NAME.
- **`os.dup2` emitted a POSITIVELY WRONG PATH.** `dup2` implicitly closes its
  target descriptor and rebinds it; leaving the target's old entry in the
  `fd -> path` map reported one file's name while the bytes landed in another.
  Fixed by EVICTING the stale entry when the source has no entry of its own.
- **The pre-context descriptor claim has TWO sub-cases and they do not agree**
  (see the NOT-SEEN set below). The earlier draft of this ADR stated one
  behaviour for both, and it was false for one of them.
- **Corpus, re-derived against THIS worktree's index rather than quoted
  forward.** Over the tracked `.py` population, `git ls-files` answers 144 files
  with the instrument's own two files staged and 142 without them; a call-form
  `unlink(` sweep answers 11 and 9 across those same two populations, a
  call-form `rmtree(` sweep answers 6 and 4, and a bare substring sweep for
  `unlink` answers 13. Every one of those figures decayed the moment this slice
  staged two files. Say which population was counted, and re-derive from
  `git ls-files` before citing any of them again.
- **`docs/LEDGER.md` lines 165 to 181** record the agreement failure this
  instrument exists to prevent. A counterparty tracer reported the same three
  figures as this tree's, and the ledger downgrades that to AGREEMENT BY LUCK:
  that tracer patched `builtins.open` alone and therefore never saw
  `Path.write_text`, while this tree's patched `io.open` from the start. The
  shared premise was that `logging.FileHandler` opens through `builtins.open`
  and never touches `pathlib`. The matching numbers are evidence about THAT
  premise and not about either measurement.

### The conclusion those measurements support

**An instrument that does not name its own blind spots converts a negative
reading into a false claim.** "0 bytes written" is never a statement about the
filesystem. It is only ever a statement about the shapes the tracer patched, and
a reader who cannot see that list will read it as the stronger claim. The
2026-09-11 measurement is exactly that failure: two tracers agreed, the
agreement was luck, and the thing that would have exposed it - a published
coverage list - existed in neither.

## Decision

**Ship `tools/write_tracer.py` as a TRACKED instrument that publishes BOTH a
covered-routes list AND an explicitly declared uncovered-routes list, and assert
the uncovered list in `tests/test_write_tracer.py` rather than only writing it
in prose.**

The asserted-not-merely-written half is the whole decision. A limits paragraph
in a docstring rots silently the first time somebody widens the patch set; a
limits list a test reads goes red instead. This tree has already learned that a
document is not a source of truth, and a comment describing coverage is a
document.

### Four op values, not three

An event carries `op` in `write`, `truncate`, `delete`, `create`. **`create` is
not a convenience.** It is the answer to the measured silent gap above: a path
that did not exist before the call and does exist after it is a mutation whose
`nbytes` is legitimately 0, and the three-op instrument reported nothing at all
for it.

Two further rules follow from wanting a reading that cannot mislead:

- **`write` and `truncate` are recorded BEFORE the wrapped call runs**, because
  bytes that may have reached disk must never be silent - a failed call that
  wrote a partial buffer is still a mutation. **`create` is recorded AFTER the
  call SUCCEEDS**, because a create that did not happen is a positively wrong
  reading.
- **A wrong path is worse than no path.** A descriptor with no entry in the
  `fd -> path` map is recorded as `<unattributed fd N>` and is never dropped,
  and `os.dup2` evicts rather than keeps a stale entry. Silence is not an answer
  and a confident wrong name is worse than an honest unattributed one. That
  ordering is a stated design rule of this instrument, not an accident of its
  implementation.

### What is covered

`COVERED_ROUTES` at `tools/write_tracer.py` lines 132 to 163 is AUTHORITATIVE,
and `tests/test_write_tracer.py` asserts it equals the module's own patch table
in both directions, so a route cannot be patched without being listed nor listed
without being patched. The list below is a SNAPSHOT taken 2026-09-11 and no
guard reads this file, so re-derive from the module before relying on it:

`builtins.open`, `io.open`, `pathlib.Path.open`, `pathlib.Path.write_text`,
`pathlib.Path.write_bytes`, `pathlib.Path.unlink`, `pathlib.Path.touch`,
`os.open`, `os.write`, `os.close`, `os.dup`, `os.dup2`, `os.fdopen`,
`os.replace`, `os.rename`, `os.remove`, `os.unlink`, `os.truncate`,
`os.ftruncate`, `os.link`, `os.symlink`, `shutil.rmtree`, `shutil.copyfile`,
`shutil.copy`, `shutil.copy2`, `shutil.copytree`, plus three routes mediated by
the wrapper around a returned file object - `<file object>.write`,
`<file object>.writelines`, `<file object>.truncate` - and one that is a MODE of
a patched opener rather than a name of its own, `<open(mode="x")>`.

`os.dup`, `os.dup2`, `os.ftruncate`, `os.link`, `os.symlink`, `Path.touch`,
`open(mode="x")` and the whole shutil copy family were added after the first
draft of this ADR was written, each because a measurement showed the route
either silent or misattributed.

Two things are covered TRANSITIVELY and are recorded here as an observation
about these interpreters rather than as a language guarantee: `Path.rename` and
`Path.replace` are not patched by name and do not need to be, because they
delegate to `os.rename` and `os.replace`, which are. Measured on CPython 3.14.4
and 3.11.9. If a future version stops delegating, that sentence is the thing
that has gone stale, and the route arms for `os.rename` and `os.replace` still
hold.

### The declared NOT-SEEN set

These routes are OUT of coverage by construction, and the instrument says so in
`UNCOVERED_ROUTES` at `tools/write_tracer.py` lines 170 to 189 rather than
leaving a reader to discover it. The set has NINE entries and this section
mirrors all nine:

- **Child-process writes** - `subprocess`, `os.system`, any exec. A patched name
  in this interpreter is not patched in another one.
- **Writes from a C extension** that reaches the filesystem without going
  through the `os` module or Python-level file objects. The patch surface is
  Python-level names; an extension calling the platform write syscall directly
  passes under all of them.
- **`mmap` stores.** A store into a mapped region is a memory write the kernel
  flushes later. No wrapped call is involved.
- **PATH ATTRIBUTION for a descriptor opened BEFORE entry and written with the
  raw `os.write(fd, data)` form.** This is the sub-case the earlier draft got
  right: the BYTES ARE RECORDED, as `<unattributed fd N>`. Only the path is
  lost.
- **EVERYTHING, BYTES INCLUDED, for a FILE OBJECT opened before entry.** This is
  the sub-case the earlier draft got wrong. A file object opened before entry is
  a plain builtin object whose `write` reaches the C-level writer with no
  wrapped name anywhere in the path, so NOTHING is recorded - not an
  unattributed event, nothing. Measured 2026-09-11 on CPython 3.14.4 and 3.11.9:
  `open(p, "wb", buffering=0)` before the context, one 9-byte write inside it, 9
  bytes on disk and zero events. **These two sub-cases must not be folded back
  into one sentence.** The earlier wording said the bytes were recorded for
  both, and that was false for this half.
- **`io.FileIO` constructed directly.** It is a C type whose `write` cannot be
  replaced. `open` and `Path.open` are covered because the wrapper sits on the
  OPENER, not on the type it returns.
- **Metadata-only operations** - `os.utime`, `os.chmod`, `os.chown`, and a touch
  of a file that ALREADY EXISTS. They change no bytes and produce no event.
- **Directory-level operations** - `os.mkdir`, `os.makedirs`, `os.rmdir`,
  `Path.mkdir`, `Path.rmdir`. Creating or removing an EMPTY directory produces
  no event. `shutil.rmtree` and the shutil copy family ARE covered, and each
  records ONE aggregate event on the tree root.
- **Anything after the context manager exits.** Every name is restored on the
  way out, including on an exception, so deferred work - a flush at interpreter
  shutdown, a background thread, an `atexit` handler - lands outside coverage.

A route family in NEITHER list is the silent class, and silence is the failure
that conservation arithmetic cannot catch. A test arm asserts that each named
family sits in exactly one of the two tuples.

## Consequences

- **This instrument still cannot certify "nothing was written". It can only
  certify "nothing was written through these routes."** That is the honest
  consequence and it is stated plainly rather than buried: the strong claim is
  not available from this instrument at any coverage level, because the NOT-SEEN
  set above is not a backlog to be burned down but a property of patching
  Python-level names from inside one interpreter. **The `create` op is the
  worked example of why that sentence has to stay.** Until it existed, the
  instrument reported "0 bytes" over lock-file creation in the machine-wide
  bucket - a true statement about bytes, and a false answer to the question
  actually being asked. The gap was closed by widening the op set, not by
  widening coverage, and the next such gap will look exactly as clean.
- A reading taken with this tracer must be reported together with its covered
  list. A bare byte figure quoted without it is the same defect in a new place.
  A reading must also say whether it is a statement about BYTES or about
  MUTATIONS, because the two now differ: a run can be honestly zero-byte and
  still carry `create` and `delete` events.
- The `os.open` plus `os.fdopen` shape at `ops/loop/slots.py:189` and
  `ops/loop/slots.py:195` is the worked example a future reader should check the
  covered list against first, because it is live, it is in the file the halt
  ruling names, and it is the shape both 2026-09-11 tracers missed.
- Byte counts are PER LOGICAL CALL, not per syscall. A re-entrancy guard means
  only the outermost wrapped call on a thread records, so `Path.write_text`
  yields one event rather than three and `shutil.copytree` yields one carrying
  the total size of the source tree. A reading compared against a syscall-level
  count will not match, and that is correct rather than a defect.
- Deletion and truncation are a separate question from writing. Whatever this
  instrument's covered list says about them, the call-form populations in the
  Context above are the corpus any such coverage has to be sized against, and
  every one of those figures decays - re-derive them from `git ls-files` before
  citing them.
- **No per-file licence header is added to the new files.** ADR-009 ruled
  against per-file headers and SPDX identifiers, the licence attaches at the
  repository level, and nothing here reopens that.

## Rejected

- **Adopting a counterparty's tracer bytes unread.** Rejected. This tree's
  standing rule is to adopt the SHAPE and to copy bytes only where the bytes ARE
  the contract, as with the CAVEMAN banner string. That file is untracked here,
  and the ledger entry at `docs/LEDGER.md` lines 165 to 181 is a measurement of
  what adopting it unread would have bought: a tracer whose patch set missed
  `Path.write_text`, producing figures that agreed with ours by luck. The shape
  is worth having. The bytes are not the contract.
- **Relying on transitive coverage for the shutil copy family.** Rejected on a
  measurement rather than on taste: `shutil.copy2` produced zero events through
  the unpatched module on CPython 3.14.4 for Windows, because `shutil.copyfile`
  takes a native fast path that never enters `open`. A coverage claim that holds
  on one platform and fails on another is the defect this ADR rules against, so
  the family is patched by name.
- **Filesystem-level auditing, such as a Windows filter driver or a kernel audit
  facility.** Rejected as out of scope. It is the only approach that would close
  the child-process and C-extension entries in the NOT-SEEN set, and that is
  exactly why it is named here rather than omitted - but it requires elevated
  privileges, it is not installable from a checkout, and an instrument a
  contributor cannot run is not an instrument this tree can depend on. If the
  strong claim is ever genuinely needed, this is where it has to come from, and
  that is a new decision rather than a widening of this one.
- **Leaving it ad-hoc.** Rejected, because the 2026-09-11 measurement is exactly
  the failure that produced. Two instruments existed, neither was tracked,
  neither published its limits, their agreement was luck, and the coverage gap
  that mattered - `os.open` plus `os.fdopen`, live in `ops/loop/slots.py` - was
  found by reading the source afterwards rather than by the instruments saying
  so. An ad-hoc tracer is rewritten from memory each session, which means its
  blind spots are rediscovered from scratch each session, or not at all.
- **Publishing the coverage list in prose only, in a docstring or in this ADR.**
  Rejected. It is the cheap version of the decision and it fails the same way
  the ad-hoc tracers failed: nothing checks it. Per this tree's guard convention
  the uncovered list needs an arm that goes red when the list and the instrument
  disagree, and it needs a non-vacuity arm proving that detector actually fires.
  This ADR is itself an instance of the rejected shape - it was drafted in
  parallel by an agent who never read the module, and by the time the module was
  repaired it misdescribed the instrument in two places. Both are corrected
  above. Neither was caught by a guard, because no guard reads this file.
