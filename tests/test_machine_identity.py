"""No tracked file may carry an absolute path naming a real user account.

WHY THIS EXISTS, and it is not hypothetical. `.claude/commands/done.md` line
172 told every wrapping-up session to look in an absolute path that spelled out
the operator's real Windows account name. The line sat in the tree, tracked and
public-bound, and NOTHING IN THIS REPOSITORY LOOKED AT IT.

The near miss is the interesting part. `tests/test_docs_consistency.py` walks
that exact file, and walks it densely - it is named in GOVERNING_DOCS precisely
because it is the densest collection of paths in the tree. But it only inspects
a backticked token that starts with one of its TREE_ROOTS (`core/`, `docs/`,
`tests/` and so on), because its question is "does this pointer resolve". A
drive-qualified absolute path starts with none of those roots, so it was never
even a candidate. The leak was not tolerated; it was invisible.

WHY THIS IS A SEPARATE FILE AND NOT A CLAUSE BOLTED ONTO THAT ONE. The two ask
different questions of the same bytes:

    test_docs_consistency.py   does a cited path RESOLVE to something on disk?
    test_machine_identity.py   does any file LEAK an identity?

A path that resolves can still leak, and a leaked path resolves on exactly one
machine. Merging them would force one sweep to serve two predicates, and the
first would go on quietly deciding what the second is allowed to see - which is
the failure this file was written in response to.

WHAT IS DELIBERATELY NOT CHECKED. Machine names, checkout locations and project
directories. `README.md` documents `C:\\Resin Compute` as the canonical clone
target and names the host it sits on, on purpose, as install instructions. The
predicate here is narrower and stateable in one line: an absolute path whose
ACCOUNT SEGMENT names a real account. Widening it to "any absolute path" would
flag the install docs and would be argued away within a session.

BREADTH COVERED, and it is a choice rather than an accident. The Windows drive
form is the measured live risk and is the form the actual leak took. The Linux
and macOS forms, and the mounted-drive spellings a Git Bash or WSL shell emits,
are covered too: all four were verified to produce ZERO matches on the tree at
the time of writing, so generalising cost no false positive, and a contributor
on any of those platforms produces the identical class of leak.

KNOWN AND ACCEPTED GAPS, stated because an undocumented limit is how the first
leak survived. Not covered, each verified missed rather than assumed:

    a UNC share             \\\\server\\Users\\<account>\\...
    percent-encoded         C:%5CUsers%5C<account>
    a bare account mention  "the <account> account", with no path at all

The first two have no occurrence in this tree and no plausible route into it.
The third is not a gap but a deliberate boundary: this guard is about absolute
paths, and matching a bare word would fire on prose and be relaxed away.
"""
from __future__ import annotations

import functools
import re
import subprocess
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

#: Resolved from this file, never from the process working directory. pytest
#: can be invoked from anywhere, and a sweep rooted at the cwd silently scans
#: the wrong tree - or nothing at all - and passes.
REPO_ROOT = Path(__file__).resolve().parent.parent

SELF = "tests/test_machine_identity.py"


# ---------------------------------------------------------------------------
# Building the offending strings WITHOUT becoming an offender
# ---------------------------------------------------------------------------
#
# This file is tracked, so the sweep below scans it. Typing a real leaking path
# as a single source literal anywhere here - in a test case, a docstring or a
# comment - would make this file the very violation it exists to catch. That
# trap has been paid for in this tree already: an ASCII-purity test that typed
# a banned glyph to demonstrate the glyph. The recorded fix is the shape used
# here - assemble the offending literal at run time from parts, so no
# contiguous run of source bytes ever spells one.
#
# The two path segments and the account name are therefore held separately and
# joined by the helpers below. Nothing in this file writes the segment word
# adjacent to a separator adjacent to an account.

_USERS_SEGMENT = "Users"
_HOME_SEGMENT = "home"

#: Split so that no single literal in this file spells a real account name.
#: Defence in depth: the helpers already keep it away from a path segment, but
#: a future edit that inlines a helper call must not silently re-create the leak.
_REAL_ACCOUNT = "Admin" + "istrator"


def _windows_path(drive: str, separator: str, account: str, *tail: str) -> str:
    """Assemble `<drive>:<sep>Users<sep><account>[<sep>tail...]` at run time.

    `separator` is passed in rather than fixed because both forms occur on disk
    and both must be caught. A Windows path written inside a Python string
    literal carries DOUBLED backslashes in the file's actual bytes, and
    tests/test_make_shortcut.py is exactly that case.
    """
    return separator.join([drive + ":", _USERS_SEGMENT, account, *tail])


def _posix_path(root: str, account: str, *tail: str) -> str:
    """Assemble `/<root>/<account>[/tail...]` at run time."""
    return "/" + "/".join([root, account, *tail])


# ---------------------------------------------------------------------------
# The predicate
# ---------------------------------------------------------------------------

#: One separator or several. Several is not decoration: see `_windows_path`.
#: A single-separator pattern walks straight past a doubled-backslash literal,
#: which is the form every Windows path in Python source actually takes.
_SEP = r"[\\/]+"

#: The account segment: everything up to the next separator, quote or space.
#:
#: DELIBERATELY WIDE. It is wide enough to capture placeholder spellings such
#: as an angle-bracketed token, so that a placeholder is exempted BY THE
#: ALLOWLIST and not by silently failing to match. A narrower class would make
#: every allowlist entry dead code and turn every "this placeholder survives"
#: assertion into a statement about nothing, which is the exact failure mode
#: this file is built to avoid. `test_the_allowlist_is_what_exempts_a_
#: placeholder` pins that down.
_ACCOUNT = r"""[^\s\\/`'"]+"""

#: `C:/Users/`, `C:\Users\`, `C:\\Users\\`, any drive letter, either case.
_WINDOWS_PREFIX = r"[A-Za-z]:" + _SEP + _USERS_SEGMENT + _SEP

#: `/Users/` (macOS) and `/home/` (Linux), but only when the slash really does
#: start an absolute path. The lookbehind rejects a preceding word character,
#: dot, tilde, hyphen or colon, which is what keeps `https://example.com/home/x`
#: and `~/home/x` and a relative `docs/Users/x` out of the sweep. Excluding the
#: colon also makes this branch provably disjoint from the Windows branch, so a
#: drive-qualified path can never be reported twice.
_POSIX_PREFIX = r"(?<![A-Za-z0-9._~:-])/(?:" + _USERS_SEGMENT + "|" + _HOME_SEGMENT + ")/"

#: The same Windows drive re-spelled as a mount: `/c/...` under MSYS,
#: `/mnt/c/...` under WSL, `/cygdrive/c/...` under Cygwin. Added because this
#: tree is developed from Git Bash - CLAUDE.md, the agent roster and the ledger
#: all discuss MSYS path rewriting - so a path pasted out of the operator's own
#: shell arrives in exactly this shape, and the plain POSIX branch above cannot
#: see it: its lookbehind rejects a preceding word character, which is what the
#: single drive letter is.
_MOUNTED_PREFIX = (
    r"(?<![A-Za-z0-9._~:-])(?:/mnt|/cygdrive)?/[A-Za-z]/" + _USERS_SEGMENT + "/"
)

ABSOLUTE_USER_PATH = re.compile(
    "(?:"
    + _WINDOWS_PREFIX
    + "|"
    + _MOUNTED_PREFIX
    + "|"
    + _POSIX_PREFIX
    + ")("
    + _ACCOUNT
    + ")",
    re.IGNORECASE,
)

#: Stripped off a captured segment before it is judged, so a path at the end of
#: a sentence or inside brackets reports the account rather than the account
#: plus punctuation. `>` is deliberately NOT here: stripping it would mangle an
#: angle-bracketed placeholder into something the allowlist no longer matches.
_TRAILING_PUNCTUATION = ".,;:!?)]}"

#: Account segments that are exempt, BY NAME AND WITH A REASON, never by
#: pattern. The by-name-with-a-reason discipline is borrowed from
#: RUNTIME_ARTIFACTS in tests/test_docs_consistency.py, and for the same cause:
#: a pattern-based exemption widens silently, and nobody notices the day it
#: starts covering a real account.
#:
#: Adding an entry is a deliberate act. If a new placeholder shows up, add it
#: here with the file that uses it and why it cannot be a real account. Do not
#: relax `_ACCOUNT` and do not add a wildcard.
PLACEHOLDER_ACCOUNTS: dict[str, str] = {
    "x": (
        "The deliberate synthetic account in the make-shortcut fixture, "
        "tests/test_make_shortcut.py. A one-letter stand-in chosen to be "
        "obviously fictional; it names no account on any machine."
    ),
    "<account>": (
        "The documentation placeholder ROADMAP.md and NEXT_SESSION_PROMPT.md "
        "use when describing this very defect. Angle brackets are not legal "
        "in a Windows path segment, so the token cannot name a real account."
    ),
    "someoperator": (
        "The deliberately fictional account in the hand-off leak fixtures, "
        "tests/test_publish_next_session.py. Those arms prove that "
        "tools/publish_next_session.py REFUSES to publish a block naming a "
        "real user profile, so they must contain an account-shaped path or "
        "they assert nothing. Chosen to be obviously invented; it names no "
        "account on this or any machine, and the real one is never used - "
        "a fixture that planted the true account name would be the leak it "
        "is testing for."
    ),
}


def leaked_accounts(text: str) -> list[str]:
    """Every account segment in `text` that is not a declared placeholder.

    This is the whole predicate. Every test below drives THIS function, so the
    teeth are proved on the predicate itself rather than by mutating the
    checkout - the tree is shared with a merge and with sibling worktrees, and
    a test that writes a decoy file into it can leave residue behind.
    """
    found: list[str] = []
    for match in ABSOLUTE_USER_PATH.finditer(text):
        account = match.group(1).rstrip(_TRAILING_PUNCTUATION)
        if not account:
            continue
        if account.lower() in PLACEHOLDER_ACCOUNTS:
            continue
        found.append(account)
    return found


# ---------------------------------------------------------------------------
# The sweep
# ---------------------------------------------------------------------------


@functools.cache
def _tracked_files() -> tuple[str, ...]:
    """Tracked paths only.

    Scoped to `git ls-files` on purpose. Untracked scratch files, the
    gitignored worktrees under `.claude/`, virtualenvs and build output are
    none of this guard's business, they are not going public with the repo,
    and sweeping them would make this test depend on whatever happens to be
    lying around.
    """
    require_git_repository()
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return tuple(line for line in completed.stdout.splitlines() if line)


@functools.cache
def _sweep() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (offenders, names actually read).

    The second half is not bookkeeping. A file walk that quietly stopped
    finding anything would satisfy the offender assertion forever, so the
    count it produces is asserted separately below.
    """
    offenders: list[str] = []
    scanned: list[str] = []
    for name in _tracked_files():
        path = REPO_ROOT / name
        if not path.is_file():
            continue  # Staged deletion; not this test's problem.
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # Binary or unreadable. Skipped, never fatal.
        scanned.append(name)
        for lineno, line in enumerate(text.splitlines(), start=1):
            for account in leaked_accounts(line):
                offenders.append(f"{name}:{lineno} names the account {account!r}")
    return tuple(offenders), tuple(scanned)


def _read(name: str) -> str:
    return (REPO_ROOT / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ARM ONE - the bad thing is gone
# ---------------------------------------------------------------------------


def test_no_tracked_file_carries_an_absolute_path_naming_a_real_account():
    offenders, _ = _sweep()
    assert not offenders, (
        "these tracked files carry an absolute path naming a real user "
        "account, and this repository is public:\n  "
        + "\n  ".join(offenders)
        + "\n\nWrite the home-relative form instead (a leading tilde), which "
        "is correct on every machine rather than on exactly one. If the "
        "segment really is a placeholder, add it to PLACEHOLDER_ACCOUNTS with "
        "the file that uses it and why it cannot name a real account. Do not "
        "widen the regex."
    )


# ---------------------------------------------------------------------------
# ARM TWO - the legitimate neighbours survived
# ---------------------------------------------------------------------------
#
# A sweep scores one hundred percent on arm one by deleting every path in the
# tree. This arm is what stops that being an acceptable answer. It has been
# earned here already: "Legion" names both this machine and a sibling project
# in ADR-004's port registry, so a blind replace on that word would have
# destroyed a real port-registry row while reporting success.


def test_the_synthetic_account_in_the_shortcut_fixture_survives():
    """tests/test_make_shortcut.py must keep its deliberately fictional path.

    It is a fixture argument. A sweep that rewrote it would be editing the
    thing under test to make the guard quiet.
    """
    fixture = "tests/test_make_shortcut.py"
    text = _read(fixture)
    # Doubled separators: the file is Python source, so one backslash in the
    # path is two backslashes in the bytes on disk.
    expected = _windows_path("C", "\\\\", "x", "Desktop", "ResinCompute.lnk")
    assert expected in text, (
        f"the synthetic account path is gone from {fixture}. It is a "
        "deliberate fictional fixture value, not a leak, and removing it "
        "means a sweep went too wide."
    )
    assert leaked_accounts(text) == []


@pytest.mark.parametrize("placeholder", sorted(PLACEHOLDER_ACCOUNTS))
def test_every_allowlisted_placeholder_still_occurs_in_the_tree(placeholder: str):
    """An exemption must keep earning its place.

    Two different failures land here and the message separates them. Either an
    over-broad sweep destroyed the documentation that describes this defect,
    or the docs legitimately stopped using the placeholder - in which case the
    allowlist entry is now an unused hole and should be deleted rather than
    kept warm.
    """
    needles = (
        _windows_path("C", "/", placeholder),
        _windows_path("C", "\\", placeholder),
        _windows_path("C", "\\\\", placeholder),
    )
    carriers = [
        name
        for name in _sweep()[1]
        if any(needle in _read(name) for needle in needles)
    ]
    assert carriers, (
        f"the placeholder {placeholder!r} no longer appears in any tracked "
        "file. Either a sweep went too wide and destroyed a legitimate "
        "neighbour, or the placeholder is genuinely unused now and its "
        "PLACEHOLDER_ACCOUNTS entry must be removed. Its stated reason was: "
        + PLACEHOLDER_ACCOUNTS[placeholder]
    )


def test_the_install_documentation_is_not_collateral_damage():
    """`README.md` names the canonical checkout path on purpose.

    It has a drive letter and a real directory but no account segment, so the
    predicate must leave it entirely alone. If a future widening of the regex
    starts flagging install instructions, it fails here first.
    """
    text = _read("README.md")
    assert "C:" + "\\" + "Resin Compute" in text
    assert leaked_accounts(text) == []


# ---------------------------------------------------------------------------
# Non-vacuity, driven at the predicate and never by mutating the checkout
# ---------------------------------------------------------------------------

_FLAGGED = [
    (
        "the real historical leak, forward slashes",
        "Check `"
        + _windows_path("C", "/", _REAL_ACCOUNT, ".claude", "projects")
        + "/` for",
    ),
    (
        "backslashes, the form Windows itself prints",
        _windows_path("C", "\\", _REAL_ACCOUNT, "Desktop", "thing.txt"),
    ),
    (
        "doubled backslashes, the form a Python string literal takes on disk",
        _windows_path("C", "\\\\", _REAL_ACCOUNT, "Desktop", "thing.txt"),
    ),
    (
        "lowercase drive and lowercase segment",
        _windows_path("c", "/", _REAL_ACCOUNT, "notes").lower(),
    ),
    (
        "a drive other than C",
        _windows_path("D", "\\", _REAL_ACCOUNT, "Desktop"),
    ),
    (
        "the Linux form",
        _posix_path(_HOME_SEGMENT, _REAL_ACCOUNT.lower(), ".claude", "projects"),
    ),
    (
        "the macOS form",
        _posix_path(_USERS_SEGMENT, _REAL_ACCOUNT.lower(), "Library"),
    ),
    (
        "the MSYS mount form, as pasted out of Git Bash on this machine",
        "/c/" + _USERS_SEGMENT + "/" + _REAL_ACCOUNT + "/notes.md",
    ),
    (
        "the WSL mount form",
        "/mnt/c/" + _USERS_SEGMENT + "/" + _REAL_ACCOUNT + "/notes.md",
    ),
    (
        "the Cygwin mount form",
        "/cygdrive/c/" + _USERS_SEGMENT + "/" + _REAL_ACCOUNT + "/notes.md",
    ),
]

_NOT_FLAGGED = [
    (
        "the allowlisted synthetic fixture account",
        _windows_path("C", "\\\\", "x", "Desktop", "ResinCompute.lnk"),
    ),
    (
        "the allowlisted documentation placeholder",
        _windows_path("C", "/", "<account>", ".claude", "projects") + "/",
    ),
    (
        "the correct home-relative form",
        "~/.claude/projects/C--Resin-Compute/memory/",
    ),
    (
        "the canonical checkout path, a drive but no account segment",
        "C:" + "\\" + "Resin Compute",
    ),
    (
        "the MSYS artefact discussed throughout the tree",
        "taskkill //F //PID rewrites a lone /F into F:/ and fails",
    ),
    (
        "a URL that merely contains the word, not a filesystem path",
        "https://example.com/" + _HOME_SEGMENT + "/alice/profile",
    ),
    (
        "a relative path inside the repo that happens to use the segment word",
        "docs/" + _USERS_SEGMENT + "/alice/notes.md",
    ),
    (
        "a URL whose path resembles the mount form",
        "https://example.com/c/" + _USERS_SEGMENT + "/alice",
    ),
]


@pytest.mark.parametrize(("label", "text"), _FLAGGED, ids=[case[0] for case in _FLAGGED])
def test_the_predicate_flags_a_real_account(label: str, text: str):
    # Case-folded on the way out only. Windows paths are case-insensitive, so
    # the SPELLING of the account must not decide whether it is caught.
    found = [account.lower() for account in leaked_accounts(text)]
    assert found == [_REAL_ACCOUNT.lower()], f"{label}: the predicate did not flag {text!r}"


@pytest.mark.parametrize(("label", "text"), _NOT_FLAGGED, ids=[case[0] for case in _NOT_FLAGGED])
def test_the_predicate_leaves_a_legitimate_string_alone(label: str, text: str):
    assert leaked_accounts(text) == [], f"{label}: false positive on {text!r}"


@pytest.mark.parametrize("placeholder", sorted(PLACEHOLDER_ACCOUNTS))
def test_the_allowlist_is_what_exempts_a_placeholder(placeholder: str):
    """The exemption must come from the allowlist, not from a regex that missed.

    Without this, a regex too narrow to see an angle-bracketed segment would
    pass every "the placeholder survives" case for entirely the wrong reason,
    and the allowlist would be decoration.
    """
    text = _windows_path("C", "/", placeholder, "Desktop")
    match = ABSOLUTE_USER_PATH.search(text)
    assert match is not None, (
        f"the regex cannot even see {placeholder!r} in {text!r}, so its "
        "allowlist entry is dead code and every survival assertion about it "
        "passes vacuously"
    )
    assert match.group(1) == placeholder
    assert leaked_accounts(text) == []


def test_every_allowlist_entry_carries_a_stated_reason():
    for account, reason in PLACEHOLDER_ACCOUNTS.items():
        assert account == account.lower(), f"{account!r} must be lowercase; lookup is case-folded"
        assert len(reason.split()) >= 8, f"{account!r} needs a real reason, not a label"


# ---------------------------------------------------------------------------
# Non-vacuity of the sweep itself
# ---------------------------------------------------------------------------


def test_the_sweep_reads_a_realistic_number_of_files():
    """A broken file walk finds no offenders and passes forever."""
    _, scanned = _sweep()
    assert len(scanned) >= 100, f"only {len(scanned)} tracked files were read"


@pytest.mark.parametrize(
    "anchor",
    ["CLAUDE.md", "README.md", "ROADMAP.md", "core/types.py", ".claude/commands/done.md"],
)
def test_the_sweep_reaches_the_files_that_actually_carry_paths(anchor: str):
    """Named individually because a root-prefix filter is how the leak survived.

    `.claude/commands/done.md` is here for the obvious reason: it is where the
    leak lived, and it sits outside every top-level source directory, so any
    sweep organised by tree root will miss it exactly the way the last one did.
    """
    assert anchor in _sweep()[1]


def test_this_file_does_not_trip_its_own_guard():
    """Read straight off disk rather than through the sweep.

    While this file is new and not yet in the index, `git ls-files` does not
    list it, so the sweep would not scan it and the check would be vacuous the
    one time it matters most.
    """
    assert leaked_accounts(_read(SELF)) == []
