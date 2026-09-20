"""Name the files a `git ls-files` corpus cannot see.

THE DEFECT THIS EXISTS TO FIX. Three guards in this tree build their corpus
from `git ls-files` - the glyph gate at `tools/precommit_gate.py`, the
sibling-name sweep at `tests/test_no_sibling_names.py`, and the docs pointer
guard at `tests/test_docs_consistency.py`. A file that is present on disk but
NOT YET TRACKED is therefore invisible to all three BY CONSTRUCTION. Measured
in this tree: a new test module passed the builder's suite run AND the
merge-seam run, then the pre-push gate refused it the moment it was committed.
Both green runs were VACUOUS for that file and NOTHING SAID SO. The cost was
the SILENCE, not the untrackedness.

THE RULING THIS IMPLEMENTS - warn and state the corpus. A guard that consumes
this helper NAMES the untracked files it did not scan and STILL PASSES. It does
NOT refuse. A refusing gate was already tried here and recorded as a defect:
see the docstring of `_untracked_python_files` in `tests/test_mypy_scope.py`,
where the count arm went red on 2026-09-07 for honest work in progress, and
"a guard that reddens for honest work in progress is one a contributor learns
to ignore".

NOTHING IN THIS MODULE RAISES TO ITS CALLER. `untracked_not_ignored` is
invoked from `tools/precommit_gate.py`, which runs from a git hook, so any
exception escaping here becomes a NON-ZERO HOOK EXIT - the warn-only mechanism
turned into a refusing gate through the back door, defeating the very ruling
above. Every degenerate input is therefore a WARNING plus a defensible return
value. Over-naming in a warning is harmless; under-naming reproduces the
original silence.

THE LOAD-BEARING DISTINCTION. "untracked" and "gitignored" are DIFFERENT SETS.

    git ls-files --others                      untracked INCLUDING ignored
    git ls-files --others --exclude-standard   untracked AND NOT ignored

This module uses the second form and only ever the second form. `moon_sync_inbox/`
is gitignored - `.gitignore:115` - and supplies the overwhelming bulk of this
repo's ignored-untracked paths: hundreds of them, growing every time a sibling
note lands. Dropping `--exclude-standard` pulls that entire tree into the
result, so a helper built on the first form would name hundreds of files on
every single run, the warning would be learned as noise and suppressed, and the
whole point would be lost. That is the same failure the ruling above rejects,
arriving by a different road. THAT RELATION is what makes the flag load-bearing
rather than decorative, and the relation is what does not drift.

NO EXACT COUNT IS RECORDED HERE, deliberately. Measured 2026-09-20 in the MAIN
checkout: untracked-not-ignored was 0, while the ignored-untracked set ran to
the low thousands with `moon_sync_inbox/` supplying the bulk. Earlier passes of
that same measurement during a SINGLE session read three different pairs of
figures as notes arrived - a literal with a half-life of hours has no business
in a committed docstring. This tree already has the finding that quoted evidence
rots while the conclusion survives; a precise number that is wrong by tomorrow is
that defect in miniature. Re-measure if you need a number, and do not pin an arm
to one.

Two consequences worth knowing. First, untracked-not-ignored being 0 on a clean
main checkout means this mechanism is SILENT there - it speaks only when there
is genuinely something unscanned to name, which is exactly what the adjudicated
ruling asked for. Second, none of this is reproducible from a linked worktree:
`moon_sync_inbox/` does not exist in one, so every count collapses to 0 and the
flag looks inert. That is the same fixture trap recorded against
`_SCRUBBED_GIT_VARS` below - measure against the main checkout or not at all.

This module writes NO STATE. It shells out, reads, and returns. It therefore
has no business with `core/atomic_io.py`, which is this tree's only sanctioned
state-write path.
"""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

LOGGER = logging.getLogger(__name__)

# `-z` is not a nicety. Without it git QUOTES any path holding a non-ASCII or
# unusual byte, and the caller would have to un-quote it correctly to get a real
# filename back. Under `-z` git emits raw NUL-separated bytes and never quotes,
# so `core.quotepath` is irrelevant here and is deliberately not configured.
_LS_FILES_UNTRACKED: tuple[str, ...] = (
    "git",
    "ls-files",
    "-z",
    "--others",
    "--exclude-standard",
)

# WHICH GIT ENV VARS DEFEAT `cwd` ON THIS EXACT COMMAND. Measured on this host
# against two scratch repos, `cwd` pinned to the real one, WITH A TRACKED FILE
# PRESENT - that last clause is the whole finding:
#
#   clean                -> rc 0, ['untracked.py']
#   GIT_DIR=decoy        -> rc 0, ['tracked.py', 'untracked.py']   HIJACKS
#   GIT_INDEX_FILE=decoy -> rc 0, ['tracked.py', 'untracked.py']   HIJACKS
#   GIT_WORK_TREE=decoy  -> rc 0, ['decoy_answer.py']              HIJACKS
#
# All three hijack, all three silently - returncode 0, empty stderr - so there
# is no failure signal to catch. They hijack in two DIFFERENT shapes, and both
# are fatal here. `GIT_WORK_TREE` swaps the work tree, so the answer describes
# the decoy. `GIT_DIR` and `GIT_INDEX_FILE` substitute the index that `--others`
# subtracts, so a file that IS tracked gets reported as untracked - a false
# "this was not scanned" claim, which is precisely this module's subject.
#
# TWO EARLIER REVISIONS OF THIS COMMENT WERE WRONG, in opposite directions, and
# both were wrong because of the FIXTURE rather than the reasoning. The first
# asserted all three "defeat cwd outright" without measuring. The second
# measured, but in a repo with NO TRACKED FILES - so `--others` had an empty
# index to subtract either way, `GIT_DIR` and `GIT_INDEX_FILE` had nothing to
# relabel, and both looked inert. It then recorded that an arm for them "would
# assert behaviour git does not currently have", which was false and would have
# stopped the next reader looking. A gate cannot fail if its fixture excludes
# the defect. Every fixture for these three vars keeps a tracked file.
#
# All three are scrubbed and ALL THREE ARE ARMED, in
# `test_an_exported_git_work_tree_does_not_hijack_the_answer` and the
# parametrized `test_an_exported_git_dir_or_index_does_not_hijack_the_answer`.
_SCRUBBED_GIT_VARS: tuple[str, ...] = (
    "GIT_WORK_TREE",
    "GIT_DIR",
    "GIT_INDEX_FILE",
)

# UNARMED, deliberately, and this comment is the reason. A hung `git ls-files`
# would otherwise block a guard forever, turning a warn-and-pass helper into an
# indefinite stall - the worst possible failure for something whose entire
# contract is "always finishes, always states the corpus". Provoking a real hang
# would mean a fake `git` on PATH or a wedged filesystem, neither of which is
# reachable from a test that must stay hermetic and fast. Measured: deleting
# `timeout=`, halving it, and deleting the `TimeoutExpired` handler each leave
# the whole module green. It is set on the argument that an unbounded wait is
# indefensible regardless of whether a test can prove it.
_GIT_TIMEOUT_SECONDS = 30


def _normalise_prefixes(
    root: Path, prefixes: Sequence[str]
) -> tuple[str, ...] | None:
    """Validate and canonicalise caller prefixes, loudly. Never raises.

    Returns `None` to mean "no filter", matching `prefixes=None`.

    THE EMPTY-SEQUENCE RULING - warn, and return the UNFILTERED set. An earlier
    revision raised `ValueError` here on the argument that "no filter" and
    "match nothing" are both defensible so neither may be guessed. That
    reasoning was right about the ambiguity and wrong about the remedy. The
    natural caller wiring is

        untracked_not_ignored(root, prefixes=[d for d in owned if (root/d).is_dir()])

    which yields `[]` on a shallow or partial checkout, or when a config key
    lists no directories. A raise there escapes into `tools/precommit_gate.py`
    and out through a git hook as a non-zero exit, which is the refusing gate
    the module docstring forbids. Warning and over-naming is harmless; refusing
    is not. It is also what this function already does for the structurally
    identical never-can-match case below, so raising was inconsistent with its
    own neighbour.

    THE SEPARATOR RULING. This is Windows, `Path` renders `\\`, and this helper
    returns `/`. A caller passing `tests\\` would have matched nothing and got a
    silent empty. Backslashes are therefore normalised to forward slashes rather
    than refused - the caller's intent is never in doubt.
    """
    if not prefixes:
        LOGGER.warning(
            "corpus statement received an empty prefix sequence for %s, which is "
            "probably an upstream bug - returning the UNFILTERED corpus rather "
            "than guessing between 'no filter' and 'match nothing'. Pass None to "
            "mean no filter.",
            root,
        )
        return None

    normalised = tuple(p.replace("\\", "/") for p in prefixes)

    for prefix in normalised:
        # The leading directory component, if the prefix names one. A prefix
        # whose directory does not exist can NEVER match, which is a caller
        # typo rather than a clean tree. Deliberately not "matched nothing":
        # on a tree with no untracked files every prefix matches nothing, and a
        # warning that fires on every healthy run is one a reader suppresses.
        head, sep, _ = prefix.rpartition("/")
        if not sep:
            continue
        if not (root / head).is_dir():
            LOGGER.warning(
                "corpus statement prefix %r names a directory that does not "
                "exist under %s, so it can never match",
                prefix,
                root,
            )

    return normalised


def untracked_not_ignored(
    root: str | Path,
    prefixes: Sequence[str] | None = None,
) -> list[str]:
    """Return the paths under `root` that are untracked and NOT gitignored.

    These are exactly the files a `git ls-files` corpus cannot see, and so
    exactly the files any guard built on such a corpus did not scan.

    Never raises. See the module docstring: this is called from a git hook, so
    an escaping exception would become a refusing gate.

    Args:
        root: directory to describe. Every git call is pinned to it via `cwd`,
            and the three git env vars that silently redirect it are scrubbed.
        prefixes: `None` means no filter. Otherwise a sequence of plain string
            prefixes; a path is kept if it starts with ANY of them, so
            `"tests/"` narrows to that directory and `"tools/corpus"` narrows
            to one file stem. Backslashes are normalised to forward slashes. An
            EMPTY sequence warns and returns the unfiltered corpus, and a prefix
            naming a non-existent directory warns - see `_normalise_prefixes`
            for why each of those is the ruling. Filtering happens here rather
            than through a git pathspec so that ordering, separators and
            validation are decided in one place.

    Returns:
        Sorted, forward-slash, `root`-relative paths. Empty when there is
        genuinely nothing untracked - and also when git failed, in which case an
        ERROR has been logged first. A SILENT empty is never returned: that is
        the exact vacuity shape this module exists to expose, and a helper that
        produced one would reproduce the defect it was written to report.
    """
    root = Path(root)

    resolved_prefixes = (
        None if prefixes is None else _normalise_prefixes(root, prefixes)
    )

    env = dict(os.environ)
    for name in _SCRUBBED_GIT_VARS:
        env.pop(name, None)

    try:
        completed = subprocess.run(
            list(_LS_FILES_UNTRACKED),
            cwd=root,
            capture_output=True,
            env=env,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        LOGGER.error(
            "corpus statement unavailable for %s: git ls-files did not finish "
            "within %d seconds",
            root,
            _GIT_TIMEOUT_SECONDS,
        )
        return []
    except OSError as exc:
        # Fires before git runs at all - a missing or unreadable `root`, or no
        # git on PATH.
        LOGGER.error(
            "corpus statement unavailable for %s: could not run git ls-files: %s",
            root,
            exc,
        )
        return []

    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        LOGGER.error(
            "corpus statement unavailable for %s: git ls-files exited %d: %s",
            root,
            completed.returncode,
            stderr,
        )
        return []

    # Decode explicitly rather than leaning on `text=True`. git writes UTF-8
    # path bytes, while Python's text mode would decode them with the host
    # locale encoding - cp1252 on this box - and mangle any non-ASCII filename.
    # `surrogateescape` keeps an undecodable byte round-trippable instead of
    # raising.
    #
    # ARMED, but NOT through a real git call, and the reason is worth keeping.
    # Measured on this host: a filename holding lone surrogates IS creatable -
    # `lone_\udcff_surrogate.py` and friends were written and listed back
    # successfully - so the obvious fixture is available. It still proves
    # nothing, because GIT ITSELF sanitises the path before emitting it:
    #
    #   b'high_\xef\xbf\xbd.py\x00lone_\xef\xbf\xbd_surrogate.py\x00...'
    #
    # those are U+FFFD replacement characters, and git's `-z` output on this
    # host is therefore ALWAYS valid UTF-8. `errors=` is unreachable via the
    # real command, which is why swapping it for `replace` leaves every
    # fixture-based arm green. An earlier revision of this comment said the
    # filename could not be created; that was assumed and is false. The arm is
    # `test_undecodable_bytes_survive_the_decode`, which feeds the raw bytes
    # through a stubbed `subprocess.run` - the same technique the sort arm uses
    # for the same reason.
    raw = completed.stdout.decode("utf-8", errors="surrogateescape")
    paths = [p for p in raw.split("\0") if p]

    if resolved_prefixes is not None:
        paths = [p for p in paths if p.startswith(resolved_prefixes)]

    return sorted(paths)
