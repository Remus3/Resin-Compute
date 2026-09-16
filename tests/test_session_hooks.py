"""A SessionStart hook must FIRE. Declaring one is not the same as running one.

WHAT IS WIRED HERE, AND WHY IT NEEDED WIRING AT ALL.

`scripts/watch_inbox.py` was correct and connected to nothing. It reported
unread `moon_sync_inbox/` notes only when a human typed it by hand, which is
precisely the state its own module docstring argues against: the durable half
of that design is a watermark on disk, and a watermark nobody reads is a file.
`.claude/settings.json` declares it as a SessionStart hook so it runs on every
session start - including the far side of `/clear`, which STARTS a session
rather than continuing one, and is therefore the boundary the operator's
`/done` then `/clear` cycle actually crosses.

TWO PROPERTIES OF THE DECLARATION ARE LOAD-BEARING.

`--mark` MUST NOT APPEAR. Reading is not acknowledging. A hook that marked on
read would advance the watermark past notes nobody saw, which is the exact
failure `scripts/watch_inbox.py` exists to prevent, and it would do it silently
once per session. The guard below covers EVERY declared command, not only the
SessionStart one, because the property belongs to the watermark and not to the
event.

NO ABSOLUTE PATH, EVER. `tests/test_machine_identity.py` sweeps every tracked
file for an absolute path naming a real account, and that leak was closed on
2026-09-06 after sitting in the tree unread. A hook command is a new place for
one to reappear, so it is guarded HERE, at the point of declaration, as well as
by that sweep - the sweep answers "does this file leak an identity" and this
answers "is this command portable at all". A drive-qualified command also
simply does not run on the CI runner.

WHY THIS FILE IS SHAPED THE WAY IT IS - THE ZERO-OUT-OF-ZERO TRAP.

A sibling project shipped a hook-target checker to four repositories. It
reported

    MISSING HOOK TARGETS: 0

in all four, and it matched NOTHING in any of them: zero missing out of zero
checked, rendered as a clean bill of health. A check that examines nothing is
indistinguishable, in its output, from a check that passes.

So every checker below returns a PAIR - `(checked, offenders)` - and every arm
asserts the CHECKED COUNT before it asserts the offender list. Asserting that a
list is empty is the trap; asserting that a specific number of things were
looked at and none of them offended is the fix.

For the same reason a missing `.claude/settings.json` FAILS here rather than
skipping. A skip would be the same zero-out-of-zero result wearing a different
colour. The failure message names the cause a reader will actually hit.

WHY THE CHECKERS TAKE THEIR INPUT AS AN ARGUMENT.

Each one is a pure function of a settings blob, so the mutation arms can drive
it with a planted blob written to `tmp_path` and prove it has teeth. Nothing
here mutates a tracked file, not even briefly: a break-revert-observe cycle on
a real file is how a parallel agent turns an unrelated suite red while somebody
else is measuring it. The convention and the reasoning are inherited from
`tests/test_agent_roster.py` and `tests/test_line_endings.py`.

EVERY SWEEP CARRIES TWO GUARDS. One says the bad thing is caught; its partner
says a legitimate neighbour SURVIVES. A checker that flagged every input would
pass the first arm of every pair while telling the reader nothing true.

WHAT IS DELIBERATELY NOT ASSERTED. That Claude Code runs a SessionStart hook
with the working directory set to the project root. That is the condition the
declared command needs and it cannot be exercised from inside the suite, so the
firing arm runs the command under `cwd=REPO_ROOT` and asserts it works THERE.
Stated rather than assumed, because the guard would otherwise read as proof of
something it never touched.
"""
from __future__ import annotations

import functools
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import NamedTuple

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent

SETTINGS = REPO_ROOT / ".claude" / "settings.json"

#: The script the SessionStart hook exists to run, repo-relative.
WATCHER = "scripts/watch_inbox.py"

#: What turns the watcher into something safe to run before EVERY prompt.
QUIET_FLAG = "--quiet-when-empty"

#: Runtime state written by `--mark`. Gitignored, and it must NOT move when a
#: hook merely reports.
WATERMARK = REPO_ROOT / "ops" / "runtime" / "inbox_seen.json"

#: A token ending in one of these is treated as a script the hook must be able
#: to find. Broader than the one suffix in use today on purpose: a hook added
#: later as a `.sh` or a `.ps1` must inherit the same existence guarantee
#: rather than quietly leave the sweep.
SCRIPT_SUFFIXES = (".py", ".sh", ".cmd", ".bat", ".ps1")

#: A session-start hook runs before the operator can type. Claude Code kills it
#: at its declared timeout, so the declaration is a promise about latency.
MAX_HOOK_TIMEOUT = 5

#: Claude Code substitutes the project root for these. Accepted and unwrapped
#: so a later edit to the self-locating form keeps resolving, and so the
#: absolute-path guard below does not have to special-case them.
PROJECT_DIR_VARS = ("${CLAUDE_PROJECT_DIR}/", "$CLAUDE_PROJECT_DIR/")

#: `X:/` or `X:\` - any drive letter, either separator.
DRIVE_QUALIFIED = re.compile(r"^[A-Za-z]:[\\/]")

#: What `scripts/watch_inbox.py` prints. All three renderings are real: the
#: report, the `--all` listing, and the fresh-clone line for a missing inbox.
#: Anchored per line so a traceback or an empty run cannot satisfy it.
#:
#: THE MISSING-INBOX LINE NOW CARRIES `UNMEASURED` and no longer says "nothing to
#: report". Clause 2 of the fleet watcher contract in RC's `docs/CHANNEL.md` v1:
#: a could-not-measure state prints ONE line carrying that token and never the
#: affirmative clean line. "nothing to report" was the affirmative clean line
#: being printed for a channel that had not been looked at.
REPORT_SHAPE = re.compile(
    r"^(?:unread: (?:none|\d+)"
    r"|all notes: (?:none|\d+)"
    r"|UNMEASURED - no inbox at .+)\s*$",
    re.MULTILINE,
)

#: What `tools/caveman_default.py` prints. A SECOND SessionStart hook was wired
#: on operator instruction 2026-09-06 and it does not print a watcher report, so
#: one shape for every hook is the wrong assertion - it would force every future
#: hook to imitate the watcher.
#:
#: Each declared hook is matched against the shape for the SCRIPT IT NAMES, and
#: a hook naming no known script is a FAILURE rather than a pass. That is the
#: non-vacuity property restated at the dispatch level: a new hook cannot be
#: added without also stating what its output must look like, so it cannot
#: silently print nothing and still be graded.
BANNER_SHAPE = re.compile(
    r"^# Output dialect: CAVEMAN ULTRA \(default, operator \d{4}-\d{2}-\d{2}\)\s*$",
    re.MULTILINE,
)

#: What `scripts/watch_inbox.py --quiet-when-empty` prints. A THIRD hook was
#: wired on `UserPromptSubmit`, because `SessionStart` fires ONCE and cannot see
#: a note that lands mid-session - which is the COMMON case on this channel.
#:
#: It runs on every prompt, so it must print NOTHING when nothing is unread: a
#: hook that speaks with nothing to say trains the reader to skip it, at which
#: point it is worse than absent because it still looks wired.
#:
#: So the accepted output is silence OR a real report, and nothing else. The
#: exit code carries the rest of the weight: a crashed run also prints nothing
#: on stdout, and only `status == 0` separates the two. Stated here rather than
#: assumed, and `test_the_user_prompt_submit_hook_speaks_when_a_note_is_unread`
#: is the ARMED half - it proves the silence is a choice and not a broken hook.
#:
#: TWO ALTERNATIVES WERE ADDED ON 2026-09-16 AND THEY ARE DIFFERENT KINDS OF FIX.
#:
#: `UNMEASURED - no inbox at ...` IS NEW BEHAVIOUR, from clause 2 of the fleet
#: watcher contract. The quiet path used to print NOTHING for a missing inbox,
#: and silence on this hook is not neutral - silence is exactly what a clean
#: inbox produces, so a watcher that could not see the channel at all read as one
#: reporting good news. It is also the normal state of a fresh clone and of every
#: worktree, because `moon_sync_inbox/` is gitignored, so this arm was previously
#: passing on a body that meant "blind" while accepting it as "clean".
#:
#: `WITHDRAWN after being shown: N` IS A PRE-EXISTING RED THIS REGEX COULD
#: ALREADY HAVE HIT, and it predates the session work entirely. At base e9b4542 a
#: withdrawal-only quiet fire printed `unread: none` followed by the withdrawal
#: block, and this pattern rejects `unread: none` - measured match=False. The arm
#: had simply never been run with a withdrawal pending. Both halves were fixed:
#: the watcher no longer prints the affirmative clean line beside a withdrawal,
#: and the withdrawal heading is admitted here.
#:
#: MATCHED WHOLE-BODY, NOT PER LINE, AND THAT IS A CORRECTION OF THIS PATTERN'S
#: ORIGINAL SHAPE RATHER THAN A REFINEMENT OF IT.
#:
#: Every version of this regex until 2026-09-16 was a set of `^...$` alternatives
#: under `re.MULTILINE`, consumed by `.search()`. That means ONE acceptable line
#: anywhere in the body passed the whole body, and everything around it was
#: unexamined. The first widening for the two clauses above made that latent
#: weakness bite: adding a `WITHDRAWN` and an `UNMEASURED` alternative
#: accidentally admitted five bodies the previous pattern refused, including the
#: EXACT base-e9b4542 defect - `unread: none` beside a withdrawal - that this same
#: regex had been used to measure as rejected. An arm that is strictly weaker than
#: it was, carrying a comment claiming it is not, is worse than a weak arm that
#: admits it.
#:
#: The pre-existing half was just as bad and was never noticed: a full traceback
#: co-occurring with `unread: 3` passed, because one good line was enough. The old
#: docstring's claim that "a traceback ... still fails" was true only of a
#: traceback ALONE.
#:
#: SO THE PATTERN NOW DESCRIBES THE WHOLE GRAMMAR THIS TOOL EMITS, anchored
#: `\A`...`\Z`. `.search()` on a fully anchored pattern is `.fullmatch()`, so the
#: call sites did not have to change. Anything the watcher does not emit - a
#: traceback, a launcher error, a raw `PermissionError`, a second UNMEASURED line,
#: or the affirmative clean line sitting beside any of them - now fails because
#: there is no alternative that can absorb it.
#:
#: `test_the_quiet_shape_matcher_accepts_silence_and_a_report_but_not_noise`
#: carries both halves, and names each of the five regressions explicitly so a
#: later widening has to defeat them one at a time rather than by accident.

#: `  [recv] 2026-09-15-from-RC-topic.md  (2 files)` - one listed entry.
_Q_ENTRY = r"[ ]{2}\[[a-z]+\] [^\n]*\n"
#: `  (+4 more)`, or the same naming the report file, or saying UNMEASURED.
_Q_POINTER = r"[ ]{2}\(\+\d+ more[^\n]*\)\n"
#: The counts line plus its names. `unread: none` is deliberately NOT here: it is
#: the affirmative clean line and clause 2 keeps it off a per-prompt hook.
_Q_REPORT = r"(?:unread|all notes): \d+\n(?:" + _Q_ENTRY + r")+(?:" + _Q_POINTER + r")?"
#: The withdrawal block, heading through its trailing hint line.
_Q_WITHDRAWN = (
    r"WITHDRAWN after being shown: \d+\n"
    r"(?:[ ]{2}\[gone\] [^\n]*\n)+"
    r"[ ]{2}\(run --mark[^\n]*\)\n"
)
#: The one could-not-measure line, clause 2. ONE, and nothing beside it.
_Q_UNMEASURED = r"UNMEASURED - no inbox at [^\n]*\n"
#: The unusable-report-record disclosure: a headline and two parenthetical lines.
_Q_UNUSABLE = (
    r"the record of what has been shown is unusable - [^\n]*\n"
    r"[ ]{2}\([^\n]*\)\n"
    r"[ ]{2}\([^\n]*\)\n"
)

QUIET_SHAPE = re.compile(
    r"\A(?:"
    r"\s*"
    r"|" + _Q_UNMEASURED +
    r"|(?:" + _Q_REPORT + r")?(?:" + _Q_WITHDRAWN + r")?(?:" + _Q_UNUSABLE + r")?"
    r")\Z"
)

#: The EXACT declared command -> the shape its stdout must carry.
#:
#: Keyed on the whole command rather than on a script basename, because two
#: hooks now name the same script under different flags and must be graded
#: differently. Exact lookup also strengthens the non-vacuity property already
#: recorded above: a hook cannot acquire a flag that changes what it prints
#: without somebody stating the new expectation here.
#: The `--source` labels are PART OF THE KEY, deliberately. Adding the flag
#: changed both watcher commands, and this table refused them until they were
#: restated here - which is the exact-lookup property working rather than an
#: inconvenience. A hook cannot acquire a flag without somebody saying what it
#: must now print, and neither of these labels changes the stdout at all.
#:
#: SO IS `$CLAUDE_PROJECT_DIR`, AND SO ARE THE DOUBLE QUOTES AROUND IT. The
#: declared script paths went absolute on 2026-09-13 at operator instruction.
#: A session's working directory DRIFTS into `moon_sync_inbox/` while notes are
#: being read, and a relative `scripts/watch_inbox.py` then resolves to
#: `<repo>/moon_sync_inbox/scripts/watch_inbox.py`, which does not exist - so
#: the UserPromptSubmit hook fails and EVERY prompt is blocked. The quotes are
#: load-bearing on top of that: this checkout path contains a real space, and
#: an unquoted expansion splits there and fails silently. Tidying either the
#: variable or the quotes away re-breaks the prompt path, and this table is
#: where that edit is forced to be noticed. The absolute-path guard still
#: passes because `PROJECT_DIR_VARS` is unwrapped before a token is judged.
EXPECTED_SHAPE = {
    'python "$CLAUDE_PROJECT_DIR/scripts/watch_inbox.py" --source sessionstart': REPORT_SHAPE,
    'python "$CLAUDE_PROJECT_DIR/scripts/watch_inbox.py" --quiet-when-empty --source userpromptsubmit': (
        QUIET_SHAPE
    ),
    'python "$CLAUDE_PROJECT_DIR/tools/caveman_default.py"': BANNER_SHAPE,
}

#: sha256 of the `_BANNER` string literal in `tools/caveman_default.py`, and its
#: length in bytes. 667 bytes, measured 2026-09-06.
#:
#: WHY A CONSTANT HERE RATHER THAN A COMPARISON AGAINST THE SIBLING COPY.
#:
#: The banner is a FLEET CONTRACT: Sibling-C, Sibling-E and this
#: tree must all emit the identical string, or four repos have quietly forked
#: one dialect while appearing to share it. The obvious guard is to diff against
#: the sibling copy, which arrived under
#: `moon_sync_inbox/from-RC-verbatim/tools/caveman_default.py`.
#:
#: THAT GUARD WOULD GO SILENT RATHER THAN RED. `moon_sync_inbox/` is gitignored
#: (`.gitignore:115`) and tracks zero files, so the reference is absent from CI
#: and from every fresh clone. A comparison against a path that does not exist
#: there either errors for the wrong reason or gets wrapped in a skip, and a
#: skipped test is a green tick. The identity was true when measured on this
#: machine and nothing in the repository held it.
#:
#: So the expectation lives HERE, in this file, as a literal. Absence of the
#: sibling tree can no longer disarm it, and changing the banner now requires
#: changing this constant in the same commit - which is the point at which
#: somebody has to say out loud that they are forking the contract.
BANNER_SHA256 = "b527af9597a3f1d3f7a853854dcd0cb6c6b616977deb60101a06da43906df535"
BANNER_BYTES = 667


def shape_for(command: str) -> re.Pattern[str]:
    """The output shape the declared command must produce.

    Raises rather than defaulting. An unrecognised command is a hook nobody has
    declared an expectation for, and grading it against a permissive default is
    how a silent hook passes.
    """
    try:
        return EXPECTED_SHAPE[command.strip()]
    except KeyError:
        raise KeyError(
            f"no output shape declared for hook command {command!r}. Add it to "
            "EXPECTED_SHAPE - a hook with no stated expectation cannot be graded."
        ) from None


class HookCommand(NamedTuple):
    event: str
    command: str
    timeout: object


# ---------------------------------------------------------------------------
# Reading the declaration
# ---------------------------------------------------------------------------


def _load_settings() -> dict:
    """The project settings blob, or a FAILURE naming why there is none."""
    assert SETTINGS.is_file(), (
        f"{SETTINGS} does not exist, so no session hook is wired and nothing "
        "runs the inbox watcher. This guard FAILS rather than skips: a skip "
        "here is the zero-out-of-zero result this file was written to prevent. "
        "If this fires in a FRESH CLONE the cause is `.gitignore`, which "
        "excludes `.claude/*` and negates only `.claude/agents/*.md` and "
        "`.claude/commands/*.md` back in - the wiring is then local to one "
        "machine and reaches nobody else."
    )
    payload = json.loads(SETTINGS.read_bytes().decode("utf-8"))
    assert isinstance(payload, dict), (
        f"{SETTINGS.name} parses to {type(payload).__name__}, not an object"
    )
    return payload


def _hook_commands(settings: dict) -> list[HookCommand]:
    """Every `type: command` hook in the blob, flattened, event first.

    The nesting is Claude Code's: event -> matcher groups -> command entries.
    Each level is type-checked as it is walked, because a blob that is merely
    the wrong SHAPE would otherwise flatten to an empty list and be read as
    "no hooks declared" - a silent zero, which is the whole failure mode here.
    """
    hooks = settings.get("hooks")
    assert isinstance(hooks, dict), (
        f"`hooks` is {type(hooks).__name__}, not an object, so no hook is declared"
    )

    found: list[HookCommand] = []
    for event in sorted(hooks):
        groups = hooks[event]
        assert isinstance(groups, list), f"hooks.{event} is {type(groups).__name__}, not a list"
        for group in groups:
            assert isinstance(group, dict), (
                f"hooks.{event} holds a {type(group).__name__}, not an object"
            )
            entries = group.get("hooks", [])
            assert isinstance(entries, list), (
                f"hooks.{event}[].hooks is {type(entries).__name__}, not a list"
            )
            for entry in entries:
                assert isinstance(entry, dict), (
                    f"hooks.{event}[].hooks holds a {type(entry).__name__}, not an object"
                )
                if entry.get("type") != "command":
                    continue
                command = entry.get("command")
                assert isinstance(command, str) and command.strip(), (
                    f"hooks.{event} declares a command hook with no command string"
                )
                found.append(HookCommand(event, command, entry.get("timeout")))
    return found


def _tokens(command: str) -> list[str]:
    """The command split the way a shell would, surrounding quotes removed.

    `posix=False` on purpose. In POSIX mode shlex treats a backslash as an
    escape and eats it, so a Windows-spelled path in a declared command would
    arrive here with its separators silently deleted - and the absolute-path
    guard would then see a token that is no longer absolute and wave it through.
    """
    return [token.strip("\"'") for token in shlex.split(command, posix=False)]


def _repo_relative(token: str) -> str:
    """A token as a repo-relative path: project-dir variable unwrapped, slashes
    normalised. Not resolved against the filesystem - resolution is the
    caller's job and the root is the caller's choice.
    """
    for prefix in PROJECT_DIR_VARS:
        if token.startswith(prefix):
            token = token[len(prefix):]
            break
    return token.replace("\\", "/")


def _script_targets(settings: dict) -> list[tuple[str, str, str]]:
    """(event, command, repo-relative script) for every script a hook names."""
    targets = []
    for hook in _hook_commands(settings):
        for token in _tokens(hook.command):
            candidate = _repo_relative(token)
            if candidate.lower().endswith(SCRIPT_SUFFIXES):
                targets.append((hook.event, hook.command, candidate))
    return targets


def _argv(command: str) -> list[str]:
    """The declared command as an argv list, ready to launch."""
    argv = []
    for token in _tokens(command):
        for prefix in PROJECT_DIR_VARS:
            if token.startswith(prefix):
                token = str(REPO_ROOT / token[len(prefix):])
                break
        argv.append(token)
    return argv


@functools.lru_cache(maxsize=1)
def _tracked_paths() -> frozenset[str]:
    """Exactly what `git ls-files` stores.

    Membership is tested against this SET rather than by running `git ls-files
    --error-unmatch <path>`, which also succeeds for a DIRECTORY that merely
    contains tracked files. The question here is whether git stores THIS PATH.
    """
    require_git_repository()
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return frozenset(line for line in completed.stdout.splitlines() if line)


# ---------------------------------------------------------------------------
# The checkers. Each returns (checked, offenders) - never a bare list, because
# an empty offender list over an empty input is the trap this file is about.
# ---------------------------------------------------------------------------


def _check_targets_on_disk(settings: dict, root: Path = REPO_ROOT) -> tuple[int, list[str]]:
    """Script targets that are not a FILE under `root`.

    `is_file()`, never `exists()`. A directory satisfies `exists()`, and git
    stores no directories, so an `exists()` check would call a target present
    that a fresh clone does not receive.
    """
    targets = _script_targets(settings)
    absent = [rel for _event, _command, rel in targets if not (root / rel).is_file()]
    return len(targets), absent


def _check_targets_tracked(settings: dict, tracked: frozenset[str]) -> tuple[int, list[str]]:
    """Script targets git does not store, so a fresh clone would not get them."""
    targets = _script_targets(settings)
    untracked = [rel for _event, _command, rel in targets if rel not in tracked]
    return len(targets), untracked


def _check_no_mark(settings: dict) -> tuple[int, list[str]]:
    """Commands that would advance the watermark. Reading is not acknowledging."""
    commands = _hook_commands(settings)
    offenders = [f"{hook.event}: {hook.command}" for hook in commands if "--mark" in hook.command]
    return len(commands), offenders


def _is_absolute(token: str) -> bool:
    if DRIVE_QUALIFIED.match(token):
        return True
    return token.startswith(("/", "\\"))


def _check_no_absolute_path(settings: dict) -> tuple[int, list[str]]:
    """Tokens that pin a hook to one machine's filesystem layout."""
    checked = 0
    offenders = []
    for hook in _hook_commands(settings):
        for token in _tokens(hook.command):
            checked += 1
            if _is_absolute(_repo_relative(token)):
                offenders.append(f"{hook.event}: {token}")
    return checked, offenders


def _watermark_bytes() -> bytes | None:
    try:
        return WATERMARK.read_bytes()
    except OSError:
        return None


# ---------------------------------------------------------------------------
# ISOLATING THE CHILD. A FIXTURE THAT MONKEYPATCHES MODULE ATTRIBUTES CANNOT
# ISOLATE A SUBPROCESS.
#
# Every arm in this file that proves a hook FIRES has to launch the declared
# command, and a launched command is a fresh interpreter with the real
# defaults. `tests/test_watch_inbox.py` redirects every `DEFAULT_` Path by
# enumeration; that is complete, and it stops at the process boundary.
#
# MEASURED 2026-09-08, with the live log deleted first: this file passed 33
# arms and left SIX REAL LINES in `ops/runtime/inbox_invocations.log`, every
# one labelled `cli` - the same label a genuine SessionStart hook fire writes.
# The same run left two PLANTED fixture keys in the live
# `ops/runtime/inbox_reported.json`: `2026-09-07-1200-from-RC-planted.md` and
# `from-RC-verbatim/`.
#
# The invocation log exists to make "does the hook fire, and does it survive
# /clear" measurable for the first time. An instrument its own suite writes to
# INDISTINGUISHABLY is not evidence about the world, and a report record
# holding fixture names is the pollution `tests/test_watch_inbox.py` documents
# at length - 24 withdrawn notes, 18 of them called `note-21.md`.
#
# So every launch below carries an environment: the runtime records go
# somewhere disposable, and the child names itself as the suite.
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _watcher_module():
    """The watcher, loaded BY PATH - `scripts/` is not an importable package.

    Loaded for its CONSTANTS: the two environment variables that are the only
    channel able to reach a child process. Reading them from the module rather
    than spelling them here means a rename in the script turns this file red
    instead of silently un-isolating the suite.
    """
    spec = importlib.util.spec_from_file_location(
        "watch_inbox_for_hook_tests", REPO_ROOT / WATCHER
    )
    assert spec is not None and spec.loader is not None, f"cannot load {WATCHER}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _live_runtime_records() -> dict[str, Path]:
    """Every record the watcher writes when nothing redirects it.

    DISCOVERED FROM THE MODULE, never listed here. A hand-written
    `ops/runtime/inbox_invocations.log` in this file goes stale the day the
    record is renamed, and the arm guarding live state would then be guarding
    a path nothing writes - passing, and looking at nothing.
    """
    watcher = _watcher_module()
    return {
        name: getattr(watcher, name)
        for name in dir(watcher)
        if name.startswith("DEFAULT_")
        and isinstance(getattr(watcher, name), Path)
        and getattr(watcher, name).parent == watcher.RUNTIME_DIR
    }


#: Sentinel for `_isolated_env(source=...)` and `_fire(source=...)`: keep the
#: suite label. It is a string the label validator can never accept - a NUL is
#: outside `[a-z0-9._-]` - so a caller that passed it by accident would fall
#: back to `cli` rather than silently writing a plausible-looking label.
#:
#: A sentinel rather than `None` meaning "default", because `None` is the value
#: one arm genuinely needs: UNSET the variable, so the `--source` flag on the
#: declared command is what labels the fire.
KEEP_SUITE_LABEL = "\0keep-suite-label"


def _isolated_env(runtime: Path, source: str | None = KEEP_SUITE_LABEL) -> dict[str, str]:
    """The environment every launch in this file uses.

    BOTH HALVES ARE LOAD-BEARING AND NEITHER IS REDUNDANT. The runtime redirect
    keeps suite bytes out of the operator's records; the source label keeps a
    suite line that does get written - a child launched some other way, a
    variable someone forgot - TELLABLE from a real hook fire. One protects the
    file, the other protects the reading.

    `source` IS APPENDED AT THE END WITH A DEFAULT, per `CLAUDE.md`: a mid-
    signature required parameter breaks every existing call. `None` unsets the
    variable entirely, which exactly one arm needs - the variable OUTRANKS the
    `--source` flag on the declared command, so an arm grading that flag has to
    take the variable out of the way. The runtime redirect is not optional in
    that case and is not made optional here: the file protection stays on every
    single launch, whatever the label says.
    """
    watcher = _watcher_module()
    env = dict(os.environ)
    env[watcher.ENV_RUNTIME_DIR] = str(runtime)
    if source == KEEP_SUITE_LABEL:
        env[watcher.ENV_INVOCATION_SOURCE] = watcher.SOURCE_SUITE
    elif source is None:
        env.pop(watcher.ENV_INVOCATION_SOURCE, None)
    else:
        env[watcher.ENV_INVOCATION_SOURCE] = source
    return env


def _isolated_lines(runtime: Path) -> list[str]:
    """The invocation lines a child left under `runtime`, if any."""
    log = runtime / _live_runtime_records()["DEFAULT_INVOCATIONS"].name
    if not log.is_file():
        return []
    return [line for line in log.read_text(encoding="ascii").splitlines() if line.strip()]


def _planted(tmp_path: Path, command: str, timeout: int = 5) -> dict:
    """A settings blob written to `tmp_path` and read back.

    Round-tripped through a real file rather than used inline, so the checkers
    are driven by something that actually parsed as JSON. Nothing tracked is
    touched: the tree is never broken to watch a guard go red.
    """
    blob = {
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": command, "timeout": timeout}]}
            ]
        }
    }
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(blob, indent=2) + "\n", encoding="ascii", newline="\n")
    return json.loads(path.read_text(encoding="ascii"))


def _repo_relative_command(command: str) -> str:
    return "/".join(_repo_relative(token) for token in _tokens(command))


# ---------------------------------------------------------------------------
# (a) NON-VACUITY FIRST. Nothing below means anything if this does not hold.
# ---------------------------------------------------------------------------


def test_the_discovery_finds_at_least_one_hook_script_target():
    """The COUNT is the assertion. `assert targets` would pass on one entry and
    fail informatively on none, but it says nothing about how many were looked
    at - and looking at nothing is the reported-clean failure this file is
    written against.
    """
    settings = _load_settings()

    commands = _hook_commands(settings)
    assert len(commands) >= 1, (
        f"the discovery scanned {len(commands)} hook commands in {SETTINGS.name}; "
        "every guard in this file would then report clean over nothing"
    )

    targets = _script_targets(settings)
    assert len(targets) >= 1, (
        f"{len(commands)} hook command(s) declared but {len(targets)} resolved to a "
        f"script target - the suffix set {SCRIPT_SUFFIXES} no longer matches what "
        "the commands name, so the existence and trackedness guards examine nothing"
    )


def test_a_session_start_event_is_declared():
    events = sorted({hook.event for hook in _hook_commands(_load_settings())})
    assert "SessionStart" in events, (
        f"no SessionStart hook is declared; the events found are {events}. "
        "SessionStart is the one that survives `/clear`, which STARTS a session"
    )


def test_a_user_prompt_submit_event_is_declared():
    """SessionStart FIRES ONCE and cannot see a note that lands mid-session.

    That is the COMMON case on this channel: a sibling drops a correction while
    the session is already running, and the operator finds out about it in the
    next cold session hours later. `UserPromptSubmit` is the event that closes
    that window, and it is why the watcher grew a quiet rendering.
    """
    events = sorted({hook.event for hook in _hook_commands(_load_settings())})
    assert "UserPromptSubmit" in events, (
        f"no UserPromptSubmit hook is declared; the events found are {events}. "
        "SessionStart alone cannot surface a note that arrives mid-session"
    )


def test_user_prompt_submit_invokes_the_watcher_quietly():
    """The per-prompt hook must be the QUIET rendering.

    Without `--quiet-when-empty` it would print `unread: none` before every
    single prompt, and a hook that speaks when it has nothing to say is one the
    reader learns to skip - at which point the real report scrolls past too.
    """
    prompt = [
        hook for hook in _hook_commands(_load_settings()) if hook.event == "UserPromptSubmit"
    ]
    assert len(prompt) >= 1, "UserPromptSubmit declares no command hook"

    naming = [hook for hook in prompt if WATCHER in _repo_relative_command(hook.command)]
    assert len(naming) == 1, (
        f"{len(naming)} of {len(prompt)} UserPromptSubmit command(s) invoke {WATCHER}: "
        f"{[hook.command for hook in prompt]}"
    )
    assert QUIET_FLAG in naming[0].command, (
        f"the per-prompt hook `{naming[0].command}` omits {QUIET_FLAG}, so it "
        "would print a report before every prompt"
    )


# ---------------------------------------------------------------------------
# (b) Targets exist AND are tracked
# ---------------------------------------------------------------------------


def test_every_hook_script_target_exists_on_disk():
    checked, absent = _check_targets_on_disk(_load_settings())
    assert checked >= 1, f"the disk check examined {checked} targets and would pass vacuously"
    assert absent == [], f"declared hook targets that are not files on disk: {absent}"


def test_every_hook_script_target_is_tracked_by_git():
    """Trackedness, not presence. A hook target git does not store is a hook
    that runs here and nowhere else - the same shape as `core.hooksPath`.
    """
    tracked = _tracked_paths()
    assert len(tracked) >= 50, (
        f"`git ls-files` returned {len(tracked)} paths, which is not a real tree; "
        "the trackedness guard below would invert"
    )

    checked, untracked = _check_targets_tracked(_load_settings(), tracked)
    assert checked >= 1, f"the trackedness check examined {checked} targets"
    assert untracked == [], (
        "declared hook targets git does not store, so a fresh clone runs a "
        f"hook whose script is absent: {untracked}"
    )


# ---------------------------------------------------------------------------
# (c) The SessionStart declaration is the right one, and it does not acknowledge
# ---------------------------------------------------------------------------


def test_session_start_invokes_the_inbox_watcher():
    session = [hook for hook in _hook_commands(_load_settings()) if hook.event == "SessionStart"]
    assert len(session) >= 1, "SessionStart declares no command hook"

    naming = [hook for hook in session if WATCHER in _repo_relative_command(hook.command)]
    assert len(naming) == 1, (
        f"{len(naming)} of {len(session)} SessionStart command(s) invoke {WATCHER}: "
        f"{[hook.command for hook in session]}"
    )


def test_no_declared_hook_marks_the_inbox_as_read():
    """READING IS NOT ACKNOWLEDGING, enforced at the declaration.

    Every command is checked, not only SessionStart: the property belongs to
    the watermark, and a `--mark` smuggled onto some other event would advance
    it just the same.
    """
    checked, offenders = _check_no_mark(_load_settings())
    assert checked >= 1, f"the mark guard examined {checked} commands"
    assert offenders == [], (
        "a hook passes --mark, which advances the watermark past notes nobody "
        f"has read: {offenders}"
    )


# ---------------------------------------------------------------------------
# (d) No absolute path, guarded where one would be introduced
# ---------------------------------------------------------------------------


def test_no_hook_command_carries_an_absolute_path():
    checked, offenders = _check_no_absolute_path(_load_settings())
    assert checked >= 2, (
        f"the absolute-path guard examined {checked} token(s); a real command "
        "carries at least an interpreter and a script"
    )
    assert offenders == [], (
        "a hook command pins itself to one machine's filesystem layout, which "
        "does not run on the CI runner and is the shape "
        f"tests/test_machine_identity.py exists to catch: {offenders}"
    )


def test_every_hook_declares_a_short_timeout():
    """A session-start hook runs before the operator can type."""
    commands = _hook_commands(_load_settings())
    assert len(commands) >= 1, f"the timeout guard examined {len(commands)} commands"
    for hook in commands:
        assert isinstance(hook.timeout, int) and not isinstance(hook.timeout, bool), (
            f"hooks.{hook.event} declares timeout {hook.timeout!r}, not an integer "
            "number of seconds"
        )
        assert 1 <= hook.timeout <= MAX_HOOK_TIMEOUT, (
            f"hooks.{hook.event} declares timeout {hook.timeout}s; a session-start "
            f"hook must finish inside {MAX_HOOK_TIMEOUT}s or it is killed"
        )


def test_the_settings_file_is_ascii_and_lf():
    """Guarded HERE as well as by the tracked-file sweeps.

    `tests/test_line_endings.py` and the CI ASCII step both select from `git
    ls-files`, so neither one sees this file until it is tracked. The bytes
    matter either way: `write_text` turns LF into CRLF on Windows and the index
    hides it, and `.gitattributes` declares `*.json text eol=lf`.
    """
    raw = SETTINGS.read_bytes()
    assert b"\r\n" not in raw, (
        f"{SETTINGS.name} carries CRLF although .gitattributes declares "
        "`*.json text eol=lf`; no diff will show this"
    )
    non_ascii = sorted({byte for byte in raw if byte > 0x7F})
    assert non_ascii == [], (
        f"{SETTINGS.name} carries non-ASCII bytes {non_ascii}; the tree is 7-bit ASCII"
    )


# ---------------------------------------------------------------------------
# (e) IT FIRES. The half that is not about the text of the declaration.
# ---------------------------------------------------------------------------


def test_the_session_start_hook_actually_fires(tmp_path):
    """Launch the declared command and read its output back off disk.

    The streams go to FILES rather than through a pipe. An exit code collected
    from a pipeline is the pipeline's, and a report read out of a pipe can be
    truncated by a full buffer without anything saying so.

    The watermark is compared before and after: the run must REPORT and must
    not ACKNOWLEDGE. That is the runtime half of the `--mark` guard above, and
    it is the one that would catch a `watch_inbox.py` that started marking on
    its own.
    """
    session = [hook for hook in _hook_commands(_load_settings()) if hook.event == "SessionStart"]
    assert len(session) >= 1, "SessionStart declares no command hook to fire"

    for index, hook in enumerate(session):
        argv = _argv(hook.command)
        assert len(argv) >= 1, f"empty command for {hook.event}"

        # Indexed, because SessionStart declares more than one command and a
        # label built from the EVENT alone has the second run overwrite the
        # first one's streams and runtime directory.
        label = f"{hook.event}-{index}"
        out_path = tmp_path / f"{label}.out"
        err_path = tmp_path / f"{label}.err"
        runtime = tmp_path / f"{label}-runtime"
        before = _watermark_bytes()

        started = time.monotonic()
        try:
            with out_path.open("wb") as out, err_path.open("wb") as err:
                status = subprocess.call(
                    argv,
                    cwd=str(REPO_ROOT),
                    env=_isolated_env(runtime),
                    stdout=out,
                    stderr=err,
                    stdin=subprocess.DEVNULL,
                )
        except OSError as exc:
            pytest.fail(
                f"the declared {hook.event} command could not be launched at all: "
                f"{argv} ({type(exc).__name__}: {exc})"
            )
        elapsed = time.monotonic() - started

        body = out_path.read_text(encoding="utf-8", errors="replace")
        noise = err_path.read_text(encoding="utf-8", errors="replace")

        assert status == 0, (
            f"{hook.event} hook `{hook.command}` exited {status}; a hook that fails "
            f"noises every session start. stderr: {noise.strip()[:400]!r}"
        )
        assert shape_for(hook.command).search(body), (
            f"{hook.event} hook `{hook.command}` exited 0 but printed no report; "
            "its stdout is injected as session context, so an empty run is a "
            f"silent hook. stdout: {body.strip()[:400]!r}"
        )
        assert "marked read" not in body, (
            f"{hook.event} hook advanced the watermark at read time: {body.strip()[:400]!r}"
        )
        assert _watermark_bytes() == before, (
            f"{WATERMARK} changed during a hook that only reports; reading is not "
            "acknowledging"
        )
        # THE ISOLATED HALF, AND IT IS THE ONE WITH TEETH. The assertion above
        # is now also satisfied by the redirect, and it was always weak on its
        # own: on a machine where no watermark exists yet, None == None passes
        # over a hook that marked. The child's OWN runtime directory starts
        # empty, so a watermark appearing there is a hook that acknowledged.
        assert not (runtime / WATERMARK.name).exists(), (
            f"{hook.event} hook `{hook.command}` wrote {WATERMARK.name} into its "
            "isolated runtime directory; reading is not acknowledging"
        )
        assert elapsed < MAX_HOOK_TIMEOUT, (
            f"{hook.event} hook took {elapsed:.2f}s against a declared ceiling of "
            f"{MAX_HOOK_TIMEOUT}s, so Claude Code would kill it"
        )


class Fired(NamedTuple):
    status: int
    body: str
    noise: str
    elapsed: float
    #: Where the child's runtime records went. Appended at the END with a
    #: default, per the convention in `CLAUDE.md`: a mid-tuple required field
    #: breaks every existing positional construction and its tests.
    runtime: Path | None = None


def _fire(
    argv: list[str], tmp_path: Path, label: str, source: str | None = KEEP_SUITE_LABEL
) -> Fired:
    """Launch `argv` at the repo root and read its streams back off disk.

    FILES rather than pipes, for both reasons the existing arm gives: an exit
    code collected from a pipeline is the pipeline's, and output read out of a
    pipe can be truncated by a full buffer without anything saying so.

    THE ENVIRONMENT IS NOT OPTIONAL HERE. See the ISOLATING THE CHILD block
    above: this launch used to write into the operator's live `ops/runtime/`,
    and the log it wrote to is the one instrument that answers whether the hook
    fires at all.
    """
    out_path = tmp_path / f"{label}.out"
    err_path = tmp_path / f"{label}.err"
    runtime = tmp_path / f"{label}-runtime"
    started = time.monotonic()
    try:
        with out_path.open("wb") as out, err_path.open("wb") as err:
            status = subprocess.call(
                argv,
                cwd=str(REPO_ROOT),
                env=_isolated_env(runtime, source),
                stdout=out,
                stderr=err,
                stdin=subprocess.DEVNULL,
            )
    except OSError as exc:
        pytest.fail(f"could not launch {argv}: {type(exc).__name__}: {exc}")
    return Fired(
        status,
        out_path.read_text(encoding="utf-8", errors="replace"),
        err_path.read_text(encoding="utf-8", errors="replace"),
        time.monotonic() - started,
        runtime,
    )


def _prompt_hooks() -> list[HookCommand]:
    return [hook for hook in _hook_commands(_load_settings()) if hook.event == "UserPromptSubmit"]


def test_the_user_prompt_submit_hook_actually_fires(tmp_path):
    """It runs, it exits 0, it does not acknowledge, and it is fast.

    The watermark is compared on its BYTES before and after. READING IS NOT
    ACKNOWLEDGING is the property that stops a subagent's start - or, here, any
    prompt the operator types - from marking a queue nobody has triaged.
    """
    hooks = _prompt_hooks()
    assert len(hooks) >= 1, "UserPromptSubmit declares no command hook to fire"

    for index, hook in enumerate(hooks):
        argv = _argv(hook.command)
        assert len(argv) >= 1, f"empty command for {hook.event}"

        before = _watermark_bytes()
        fired = _fire(argv, tmp_path, f"{hook.event}-{index}")

        assert fired.status == 0, (
            f"{hook.event} hook `{hook.command}` exited {fired.status}; this one runs "
            f"before EVERY prompt. stderr: {fired.noise.strip()[:400]!r}"
        )
        assert shape_for(hook.command).search(fired.body), (
            f"{hook.event} hook `{hook.command}` printed something that is neither "
            f"silence nor a report: {fired.body.strip()[:400]!r}"
        )
        assert "marked read" not in fired.body, (
            f"{hook.event} hook advanced the watermark at read time: "
            f"{fired.body.strip()[:400]!r}"
        )
        assert _watermark_bytes() == before, (
            f"{WATERMARK} changed during a hook that only reports; reading is not "
            "acknowledging, and this hook fires on every prompt"
        )
        assert fired.runtime is not None and not (fired.runtime / WATERMARK.name).exists(), (
            f"{hook.event} hook `{hook.command}` wrote {WATERMARK.name} into its "
            "isolated runtime directory; this one fires before EVERY prompt"
        )
        assert fired.elapsed < MAX_HOOK_TIMEOUT, (
            f"{hook.event} hook took {fired.elapsed:.2f}s against a ceiling of "
            f"{MAX_HOOK_TIMEOUT}s, and it runs before every prompt"
        )


def test_the_user_prompt_submit_hook_speaks_when_a_note_is_unread(tmp_path):
    """THE ARMED HALF, and the reason the silence arm above means anything.

    A hook that crashed, or that pointed at nothing, would also print nothing -
    and `QUIET_SHAPE` accepts silence. So the declared command is fired a second
    time against a PLANTED inbox under `tmp_path`, where a report is the only
    correct answer. Nothing in the repository is touched: the real inbox and the
    real watermark are never the fixture.
    """
    hooks = [hook for hook in _prompt_hooks() if WATCHER in _repo_relative_command(hook.command)]
    assert len(hooks) == 1, f"expected exactly one watcher hook, found {len(hooks)}"

    inbox = tmp_path / "planted_inbox"
    inbox.mkdir()
    (inbox / "2026-09-07-1200-from-RC-planted.md").write_bytes(b"planted\n")
    (inbox / "from-RC-verbatim").mkdir()
    (inbox / "from-RC-verbatim" / "gate.py").write_bytes(b"payload\n")
    state = tmp_path / "planted_state.json"

    argv = _argv(hooks[0].command) + ["--dir", str(inbox), "--state", str(state)]
    fired = _fire(argv, tmp_path, "UserPromptSubmit-armed")

    assert fired.status == 0, f"exited {fired.status}; stderr: {fired.noise.strip()[:400]!r}"
    assert "unread: 2" in fired.body, (
        "the quiet hook printed no report over a planted note AND a planted "
        f"subdirectory drop, so its silence proves nothing: {fired.body!r}"
    )
    assert "2026-09-07-1200-from-RC-planted.md" in fired.body
    assert "from-RC-verbatim/" in fired.body, (
        "the drop did not surface; a subdirectory payload is a first-class entry"
    )
    assert not state.exists(), "a reporting run created the watermark it was handed"


def test_a_fired_hook_labels_itself_as_the_suite_in_its_own_log(tmp_path):
    """THE ENFORCED-GATE ARM FOR THE LABELLING, on the DECLARED command.

    An arm on `resolve_source`'s return value proves nothing about the path
    `.claude/settings.json` actually names. This one fires the declared hook
    command and reads the entry-point column back off disk, which is the only
    thing that says the `__main__` guard consults the variable at all.

    THE LABEL IS THE POINT OF THE WHOLE SECTION. A suite line that reads `cli`
    is indistinguishable from a genuine session start, and an operator counting
    hook fires in that log would be counting this test.
    """
    hooks = [
        hook
        for hook in _hook_commands(_load_settings())
        if WATCHER in _repo_relative_command(hook.command)
    ]
    assert len(hooks) >= 1, "no declared hook runs the watcher, so this arm is vacuous"

    watcher = _watcher_module()
    for index, hook in enumerate(hooks):
        fired = _fire(_argv(hook.command), tmp_path, f"labelled-{index}")
        assert fired.status == 0, f"stderr: {fired.noise.strip()[:400]!r}"
        assert fired.runtime is not None

        lines = _isolated_lines(fired.runtime)
        assert lines, (
            f"`{hook.command}` left no invocation line at all, so the log cannot "
            "answer whether the hook fired"
        )
        sources = {line.split("\t")[1] for line in lines}
        assert sources == {watcher.SOURCE_SUITE}, (
            f"a suite-launched hook labelled itself {sources}; "
            f"{watcher.SOURCE_CLI!r} would be indistinguishable from a real fire"
        )


#: Set for a NESTED run so the arm below does not re-enter itself. A recursion
#: guard rather than a skip-when-inconvenient: without it the nested run
#: launches its own nested run and the suite never terminates.
NESTED_MARKER = "RESINCOMPUTE_HOOK_SUITE_NESTED"

#: A literal ceiling on the nested run, never derived from anything it
#: measures. A fixture sized from the value under test is an amplifier - this
#: tree measured one that wrote 492674 files.
NESTED_TIMEOUT_SECONDS = 600


#: WHAT A NESTED-RUN CHILD CALLS ITSELF WHEN NOTHING ISOLATES IT, and the whole
#: discriminator of the arm below. A fresh value is minted per run and stamped
#: into the one environment variable `scripts/watch_inbox.py` reads when it
#: labels a line, so a launch site inside the nested run that forgets
#: `_isolated_env` inherits it and writes THIS RUN'S token into the operator's
#: live log. No external writer can write a value invented microseconds ago.
#:
#: SHAPED TO THE WATCHER'S OWN LABEL VALIDATOR, `[a-z0-9][a-z0-9._-]{0,31}`. A
#: token that validator rejects is replaced by the `cli` fallback, so it would
#: never reach a log line and the arm could never fire. The arm therefore
#: PROVES the shape against the module rather than trusting this spelling.
NESTED_TOKEN_PREFIX = "suite-probe-"

#: Entry-point labels belonging to this suite alone, named by MODULE ATTRIBUTE
#: so a rename in the watcher turns this file red rather than silent.
#:
#: `SOURCE_CLI` IS DELIBERATELY ABSENT. A bare `python scripts/watch_inbox.py`
#: typed in a terminal writes it, so it is the operator's label to write and a
#: new `cli` line is not attributable to the suite. `suite` and `main` are:
#: a NEW one in the live log is a suite write whatever else happened, which
#: catches the HALF-ISOLATED launch - a caller that passed the source label and
#: forgot the runtime redirect, where no token is stamped to find.
SUITE_ONLY_LABEL_ATTRS = ("SOURCE_SUITE", "SOURCE_MAIN")


def _label_counts(raw: bytes) -> dict[str, int]:
    """How many lines of an invocation log carry each entry-point label.

    COUNTS RATHER THAN A DIFF OF THE TWO FILES. `log_invocation` does not
    append - it rebuilds the file from a capped tail - so the before bytes are
    not guaranteed to be a prefix of the after bytes and prefix arithmetic
    would be wrong at the cap. Trimming can only LOWER a count, so "this label
    appears more often than it did" stays true across a trim.
    """
    counts: dict[str, int] = {}
    for line in raw.decode("ascii", errors="replace").splitlines():
        columns = line.split("\t")
        if len(columns) >= 2:
            counts[columns[1]] = counts.get(columns[1], 0) + 1
    return counts


def test_this_file_stamps_nothing_into_the_live_runtime_records(monkeypatch):
    """A SUITE RUN MUST NOT WRITE INTO THE INSTRUMENT IT IS MEASURING.

    NARROWED, AND SAID PLAINLY. This runs `tests/test_session_hooks.py`, not
    the whole of `python -m pytest tests`. A nested full-suite run costs
    minutes on every invocation of this one arm, and this file is the only one
    in the suite that launches the watcher as a child process - which is the
    entire exposure. The full-run claim belongs to a measurement in the
    session record, not to this arm, and this arm does not make it.

    IT ATTRIBUTES THE WRITE INSTEAD OF DETECTING A DIFFERENCE, AND THAT IS A
    BUG FIX RATHER THAN A PREFERENCE. The previous shape snapshotted the record
    bytes, ran the nested run, and failed on any difference. Those records are
    SHARED LIVE STATE: `.claude/settings.json` wires `UserPromptSubmit` to the
    watcher, so the operator's own hook appends to the live log on EVERY prompt
    of an interactive session. Any such fire landing inside the nested-run
    window - seconds, against a timeout ceiling of minutes - failed the arm and
    BLAMED THE SUITE for a write the suite did not make. Measured 2026-09-12:
    one run gave `1 failed, 2719 passed` and an immediate re-run of the
    identical tree gave `2720 passed`, and an induced append from a separate
    process reproduced it on demand. A false red in the pre-push gate blocks a
    push for a reason that is not there.

    THE DISCRIMINATOR IS A PER-RUN TOKEN. The nested run is launched with
    `RESINCOMPUTE_INVOCATION_SOURCE` set to a value minted here, which is the
    channel `resolve_source` reads to label every line it writes. A child
    launched WITHOUT `_isolated_env` inherits this environment, so it writes
    the token into the live log and the arm fires for exactly the real defect.
    An external writer cannot produce the token, so the race is gone rather
    than tolerated - no control run, no retry, no flake.

    THE SECOND ASSERTION COVERS THE HALF-ISOLATED LAUNCH, which stamps no
    token: a caller that overrides the label and not the runtime directory
    writes `suite` into the live log. See `SUITE_ONLY_LABEL_ATTRS`.

    THE RECORDS ARE DISCOVERED FROM THE MODULE. A new runtime record added
    tomorrow is covered today; a hand-written list would have been correct on
    the day it was written and silent ever after.
    """
    if os.environ.get(NESTED_MARKER):
        pytest.skip("nested run - see NESTED_MARKER, this arm must not re-enter itself")

    watcher = _watcher_module()
    assert watcher.ENV_RUNTIME_DIR not in os.environ, (
        f"{watcher.ENV_RUNTIME_DIR} is set in this run's environment, so what this "
        "arm calls the live records are not the live records and it would measure "
        "nothing. Unset it and run again"
    )

    records = _live_runtime_records()
    assert len(records) >= 3, (
        f"the discovery found almost nothing, so this arm is vacuous: {sorted(records)}"
    )

    token = NESTED_TOKEN_PREFIX + uuid.uuid4().hex[:12]
    monkeypatch.setenv(watcher.ENV_INVOCATION_SOURCE, token)
    assert watcher.resolve_source(watcher.SOURCE_CLI) == token, (
        f"the watcher refuses {token!r} as an entry-point label and falls back, so "
        "the token can never reach a log line and the arm below could never fail. "
        f"The label shape or its ceiling in {WATCHER} has moved - see resolve_source"
    )

    needle = token.encode("ascii")

    def _stamped() -> list[str]:
        return sorted(
            name
            for name, path in records.items()
            if path.is_file() and needle in path.read_bytes()
        )

    assert _stamped() == [], (
        f"{token!r} is in the live records BEFORE the nested run, so the check "
        "after it would be a statement about somebody else's bytes"
    )

    invocations = records["DEFAULT_INVOCATIONS"]
    before_counts = _label_counts(invocations.read_bytes() if invocations.is_file() else b"")

    env = dict(os.environ)
    env[NESTED_MARKER] = "1"
    env[watcher.ENV_INVOCATION_SOURCE] = token
    done = subprocess.run(
        [sys.executable, "-m", "pytest", f"tests/{Path(__file__).name}", "-q"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=NESTED_TIMEOUT_SECONDS,
    )

    stamped = _stamped()
    assert stamped == [], (
        "a run of this file stamped ITS OWN entry-point label into the operator's "
        f"live runtime records {stamped} ({token!r}). Every launch here must carry "
        "_isolated_env; a launch site added without it inherits this run's "
        "environment and writes suite lines into the one instrument that answers "
        "whether the SessionStart hook fires"
    )

    after_counts = _label_counts(invocations.read_bytes() if invocations.is_file() else b"")
    grew = sorted(
        label
        for label in (getattr(watcher, attr) for attr in SUITE_ONLY_LABEL_ATTRS)
        if after_counts.get(label, 0) > before_counts.get(label, 0)
    )
    assert grew == [], (
        f"the live invocation log gained {grew} line(s) across the nested run. Those "
        "labels are this suite's alone, so a launch redirected its LABEL and not its "
        "runtime directory - _isolated_env sets both and neither half is optional"
    )

    assert done.returncode == 0, (
        "the nested run of this file failed, so the comparison above is a "
        f"statement about a broken run: {done.stdout.strip()[-800:]!r}"
    )


# ---------------------------------------------------------------------------
# (f) MUTATION ARMS. Every checker above is driven with a planted blob written
# to tmp_path, and each pairs a fires-on-the-bad-case arm with a
# leaves-the-good-case-alone arm.
# ---------------------------------------------------------------------------


def test_the_disk_check_reports_a_target_that_is_not_there(tmp_path):
    settings = _planted(tmp_path, "python scripts/no_such_hook_target.py")
    checked, absent = _check_targets_on_disk(settings)
    assert checked == 1
    assert absent == ["scripts/no_such_hook_target.py"]


def test_the_disk_check_leaves_a_real_target_alone(tmp_path):
    """The surviving-neighbour half. A checker that flagged EVERY target would
    satisfy the arm above while saying nothing true about the tree.
    """
    settings = _planted(tmp_path, f"python {WATCHER}")
    checked, absent = _check_targets_on_disk(settings)
    assert checked == 1
    assert absent == []


def test_the_disk_check_rejects_a_directory_that_merely_exists(tmp_path):
    """The measured trap: `exists()` is true for a directory git never stores.

    Resolved against `tmp_path` rather than the repository, so the decoy is a
    real directory on a real filesystem and nothing tracked is created.
    """
    decoy = tmp_path / "scripts" / "decoy.py"
    decoy.mkdir(parents=True)
    assert decoy.exists(), "the decoy must satisfy exists() or this arm proves nothing"
    assert not decoy.is_file()

    settings = _planted(tmp_path, "python scripts/decoy.py")
    checked, absent = _check_targets_on_disk(settings, root=tmp_path)
    assert checked == 1
    assert absent == ["scripts/decoy.py"]


def test_the_tracked_check_reports_a_target_git_does_not_store(tmp_path):
    settings = _planted(tmp_path, f"python {WATCHER}")
    checked, untracked = _check_targets_tracked(settings, frozenset({"scripts/something_else.py"}))
    assert checked == 1
    assert untracked == [WATCHER]


def test_the_tracked_check_accepts_a_target_git_does_store(tmp_path):
    settings = _planted(tmp_path, f"python {WATCHER}")
    checked, untracked = _check_targets_tracked(settings, frozenset({WATCHER}))
    assert checked == 1
    assert untracked == []


def test_the_mark_guard_fires_on_a_declaration_that_acknowledges(tmp_path):
    settings = _planted(tmp_path, f"python {WATCHER} --mark")
    checked, offenders = _check_no_mark(settings)
    assert checked == 1
    assert len(offenders) == 1
    assert "--mark" in offenders[0]


def test_the_mark_guard_leaves_a_reporting_declaration_alone(tmp_path):
    settings = _planted(tmp_path, f"python {WATCHER}")
    checked, offenders = _check_no_mark(settings)
    assert checked == 1
    assert offenders == []


#: Absolute spellings a hook could plausibly acquire. Deliberately rooted at
#: `/opt` and `//fileserver` rather than at a home directory, so this file
#: cannot become an offender under tests/test_machine_identity.py while
#: demonstrating the guard.
PLANTED_ABSOLUTE = (
    "D:/opt/pytools/watch.py",
    "D:\\opt\\pytools\\watch.py",
    "/opt/pytools/watch.py",
    "//fileserver/share/watch.py",
)


@pytest.mark.parametrize("absolute", PLANTED_ABSOLUTE)
def test_the_absolute_path_guard_fires_on_each_spelling(absolute: str, tmp_path):
    settings = _planted(tmp_path, f"python {absolute}")
    checked, offenders = _check_no_absolute_path(settings)
    assert checked == 2, f"expected an interpreter and a path, tokenised {checked}"
    assert len(offenders) == 1, f"{absolute!r} was not flagged: {offenders}"
    assert absolute.replace("\\", "/") in offenders[0].replace("\\", "/")


def test_the_absolute_path_guard_leaves_a_relative_command_alone(tmp_path):
    settings = _planted(tmp_path, f"python {WATCHER}")
    checked, offenders = _check_no_absolute_path(settings)
    assert checked == 2
    assert offenders == []


def test_the_report_shape_matcher_tells_a_report_from_noise():
    """Non-vacuity for the firing arm. If this pattern stopped matching the
    watcher's real output the arm above would fail loudly; if it matched
    ANYTHING it would pass over a crash.
    """
    for good in (
        "unread: none\n",
        "unread: 2\n  [recv] a.md\n  [sent] b.md\n",
        "all notes: none\n",
        "UNMEASURED - no inbox at /opt/checkout/moon_sync_inbox, so the channel "
        "was not examined\n",
        # The capped rendering, with the pointer at this project's report file.
        "unread: 25\n  [recv] z.md\n  (+15 more, listed in full in "
        "/opt/checkout/ops/runtime/inbox_report.txt)\n",
    ):
        assert REPORT_SHAPE.search(good), f"real watcher output not matched: {good!r}"

    for bad in (
        "",
        'Traceback (most recent call last):\n  File "x", line 1\n',
        "unread\n",
        "python: can't open file 'scripts/watch_inbox.py'\n",
        # THE RETIRED WORDING MUST NOW FAIL. Clause 2 forbids the affirmative
        # clean line for a state nobody measured, so if this spelling ever comes
        # back it is a regression rather than a harmless rephrasing.
        "no inbox at /opt/checkout/moon_sync_inbox - nothing to report\n",
    ):
        assert not REPORT_SHAPE.search(bad), f"noise matched the report shape: {bad!r}"


def test_the_quiet_shape_matcher_accepts_silence_and_a_report_but_not_noise():
    """Non-vacuity for the per-prompt arm.

    `QUIET_SHAPE` deliberately accepts an EMPTY body - that is the whole point
    of the hook - so it has to reject everything else, or the firing arm would
    pass over a broken hook that happened to print an error.
    """
    for good in (
        "",
        "\n",
        "unread: 1\n  [recv] a.md\n",
        "unread: 2\n  [recv] from-RC-verbatim/  (48 files)\n  [recv] a.md\n",
        # The could-not-measure line, clause 2. This is the body a fresh clone
        # and every worktree produce, and it used to be silence.
        "UNMEASURED - no inbox at /opt/checkout/moon_sync_inbox, so the channel "
        "was not examined\n",
        # A withdrawal-only quiet fire. The PRE-EXISTING red: at base e9b4542
        # this body began `unread: none` and was rejected here.
        "WITHDRAWN after being shown: 1\n  [gone] a.md\n"
        "  (run --mark to acknowledge; they are carried until you do)\n",
        # The capped rendering with the overflow pointer, and the degraded
        # pointer that says so with UNMEASURED rather than naming a missing file.
        "unread: 25\n  [recv] z.md\n  (+15 more, listed in full in "
        "/opt/checkout/ops/runtime/inbox_report.txt)\n",
        "unread: 25\n  [recv] z.md\n  (+15 more - UNMEASURED, the full listing "
        "could not be written)\n",
    ):
        assert QUIET_SHAPE.search(good), f"a legitimate quiet body was rejected: {good!r}"

    for bad in (
        'Traceback (most recent call last):\n  File "x", line 1\n',
        "python: can't open file 'scripts/watch_inbox.py'\n",
        # STILL BAD, AND FOR A SHARPER REASON THAN BEFORE. `unread: none` ALONE
        # is the affirmative clean line, and clause 2 keeps it off a per-prompt
        # hook. What changed is that the watcher no longer emits it beside a
        # withdrawal, so admitting the withdrawal heading above did not have to
        # admit this.
        "unread: none\n",
        "no inbox at /opt/checkout/moon_sync_inbox - nothing to report\n",
        # The retired affirmative wording, and a bare mention of the token with
        # no line this tool emits - so the new alternatives cannot be satisfied
        # by an error message that happens to contain the word.
        "UNMEASURED\n",
        "some tool said UNMEASURED about something else\n",
    ):
        assert not QUIET_SHAPE.search(bad), f"noise matched the quiet shape: {bad!r}"


#: THE FIVE BODIES THE FIRST WIDENING OF `QUIET_SHAPE` ACCIDENTALLY ADMITTED, and
#: a sixth that the pattern had been letting through since it was written.
#:
#: Each was REJECTED by the pre-widening pattern and ACCEPTED by the widened one,
#: measured by an adversary against the version at 4d7ff31. The cause was
#: structural rather than a bad alternative: `^...$` alternatives under
#: `re.MULTILINE` consumed by `.search()` pass the whole body on ONE matching
#: line, so every widening silently widened by more than it said.
#:
#: Listed here as data with the reason each one must fail, so a future widening
#: has to defeat them individually and on purpose.
_QUIET_REGRESSIONS = (
    (
        "unread: none\nWITHDRAWN after being shown: 1\n  [gone] a.md\n"
        "  (run --mark to acknowledge; they are carried until you do)\n",
        "the affirmative clean line beside a withdrawal - the EXACT base-e9b4542 "
        "defect this same regex was used to measure as rejected",
    ),
    (
        "unread: none\nUNMEASURED - no inbox at /opt/x/moon_sync_inbox\n",
        "the affirmative clean line beside UNMEASURED, which clause 2 forbids "
        "outright - a channel cannot be both clean and unexamined",
    ),
    (
        "some arbitrary junk nobody emits\nWITHDRAWN after being shown: 1\n"
        "  [gone] a.md\n  (run --mark to acknowledge; they are carried until you do)\n",
        "arbitrary junk carried in beside a legitimate withdrawal heading",
    ),
    (
        "PermissionError: [WinError 5] Access is denied: 'C:\\\\x\\\\y.txt'\n"
        "UNMEASURED - no inbox at /opt/x/moon_sync_inbox\n",
        "a raw error string beside UNMEASURED; this tree forbids a raw API or "
        "error string on any user-facing surface, and the path is a "
        "machine-identity leak as well",
    ),
    (
        "UNMEASURED - no inbox at /opt/x\nUNMEASURED - no inbox at /opt/y\n",
        "TWO could-not-measure lines, where clause 2 says ONE",
    ),
    (
        'Traceback (most recent call last):\n  File "x", line 1\nunread: 3\n'
        "  [recv] a.md\n",
        "a traceback co-occurring with a real report. This one is NOT from the "
        "widening - the per-line `.search()` shape let it through from the "
        "beginning, and the docstring claiming tracebacks fail was true only of "
        "a traceback alone",
    ),
)


@pytest.mark.parametrize("body,why", _QUIET_REGRESSIONS)
def test_the_quiet_shape_refuses_every_body_the_widening_let_through(body, why):
    """THE ANTI-REGRESSION ARM FOR `QUIET_SHAPE` ITSELF.

    The arm above states the pattern's intent. This one states what it must never
    do again, which is a different and less forgiving property: a widening that
    satisfies the intent while re-admitting any of these is the failure that
    actually happened.
    """
    assert not QUIET_SHAPE.search(body), f"QUIET_SHAPE accepted {why}: {body!r}"


def test_the_quiet_shape_is_anchored_so_one_good_line_cannot_carry_a_body():
    """THE STRUCTURAL PROPERTY, asserted directly rather than through examples.

    Every body in `_QUIET_REGRESSIONS` is an instance of one root cause: an
    unanchored per-line pattern. Six examples do not stop a seventh, but the
    anchors do, so the anchors are asserted on the pattern itself.
    """
    assert QUIET_SHAPE.pattern.startswith(r"\A"), QUIET_SHAPE.pattern
    assert QUIET_SHAPE.pattern.endswith(r"\Z"), QUIET_SHAPE.pattern
    assert not QUIET_SHAPE.flags & re.MULTILINE, (
        "MULTILINE is back, which makes `^` and `$` line anchors again and "
        "restores the one-good-line-carries-the-body hole"
    )
    legitimate = "unread: 1\n  [recv] a.md\n"
    assert QUIET_SHAPE.search(legitimate), "the anchors rejected real output"
    assert not QUIET_SHAPE.search("noise\n" + legitimate), (
        "a prefix line was absorbed, so the body is still not matched whole"
    )
    assert not QUIET_SHAPE.search(legitimate + "noise\n"), (
        "a suffix line was absorbed, so the body is still not matched whole"
    )


def test_the_shape_lookup_refuses_a_command_nobody_has_graded():
    """A hook that acquires a flag changing its output must state the new
    expectation. Grading it against a permissive default is how a silent hook
    passes, and an EXACT lookup is what forces the statement.
    """
    with pytest.raises(KeyError):
        shape_for("python scripts/watch_inbox.py --some-future-flag")

    for command in EXPECTED_SHAPE:
        assert shape_for(command) is EXPECTED_SHAPE[command]


def test_every_declared_command_has_a_stated_output_shape():
    """The bridge from the table to the tree. EXPECTED_SHAPE could be complete
    and correct while naming a command nobody declares, or the reverse.
    """
    commands = _hook_commands(_load_settings())
    assert len(commands) >= 3, (
        f"{len(commands)} hook command(s) declared; SessionStart carries two and "
        "UserPromptSubmit carries the quiet watcher"
    )
    ungraded = []
    for hook in commands:
        try:
            shape_for(hook.command)
        except KeyError:
            ungraded.append(f"{hook.event}: {hook.command}")
    assert ungraded == [], f"declared hooks with no stated output shape: {ungraded}"


def test_the_hook_walker_reports_a_blob_that_declares_nothing(tmp_path):
    """A structurally valid but empty declaration must flatten to zero, and the
    non-vacuity arm at the top of this file is what turns that zero into red.
    """
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"hooks": {"SessionStart": [{"hooks": []}]}}, indent=2) + "\n",
        encoding="ascii",
        newline="\n",
    )
    settings = json.loads(path.read_text(encoding="ascii"))
    assert _hook_commands(settings) == []
    assert _script_targets(settings) == []


# ---------------------------------------------------------------------------
# The banner is a fleet contract, pinned against a constant in THIS file
# ---------------------------------------------------------------------------


def _banner_literal() -> bytes:
    """The `_BANNER` string literal, read by AST rather than by running it.

    AST rather than import: importing would execute the module, and a hook body
    is exactly the kind of file that is allowed to write to stdout at import
    time. Reading the literal asks about the source, which is what is pinned.
    """
    import ast

    source = (REPO_ROOT / "tools" / "caveman_default.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == "_BANNER":
                return ast.literal_eval(node.value).encode("utf-8")
    raise AssertionError(
        "tools/caveman_default.py no longer defines a module-level _BANNER "
        "string literal, so the fleet contract cannot be checked at all"
    )


def test_the_caveman_banner_matches_the_pinned_fleet_contract():
    """The banner bytes are the contract shared with the sibling repos.

    Pinned as a literal here rather than diffed against
    `moon_sync_inbox/from-RC-verbatim/`, which is gitignored and therefore
    absent in CI and in every fresh clone. See BANNER_SHA256.
    """
    import hashlib

    banner = _banner_literal()
    assert len(banner) == BANNER_BYTES, (
        f"the CAVEMAN banner is {len(banner)} bytes, pinned at {BANNER_BYTES}. "
        "It is a fleet contract shared with Sibling-C and Sibling-E; "
        "changing it forks the dialect. Update BANNER_SHA256 and BANNER_BYTES in "
        "the same commit, and tell the siblings."
    )
    digest = hashlib.sha256(banner).hexdigest()
    assert digest == BANNER_SHA256, (
        f"the CAVEMAN banner hashes to {digest}, pinned at {BANNER_SHA256}. "
        "See the message above - this is a cross-repo contract, not local prose."
    )


def test_the_banner_pin_is_not_vacuous():
    """A mutated banner must FAIL the pin, proving the arm above has teeth.

    Mutation happens on a local copy of the BYTES. Nothing on disk is touched:
    a break-revert-observe cycle on a tracked file is how a parallel agent turns
    an unrelated suite red while somebody else is measuring it.
    """
    import hashlib

    banner = _banner_literal()
    mutant = banner.replace(b"CAVEMAN ULTRA", b"CAVEMAN ULTRAA", 1)
    assert mutant != banner, "the mutation did not change the bytes; it proves nothing"
    assert hashlib.sha256(mutant).hexdigest() != BANNER_SHA256
    assert len(mutant) != BANNER_BYTES


# ---------------------------------------------------------------------------
# (g) THE ENTRY-POINT LABEL, AND IT IS AN ENFORCED-GATE SECTION.
#
# `.claude/settings.json` wires BOTH `SessionStart` AND `UserPromptSubmit` to
# `scripts/watch_inbox.py`, and the watcher's `__main__` guard fell back to one
# label - `cli` - for both, and for a manual terminal run as well. Measured
# 2026-09-08 at HEAD 0e9491a: every fire in the complete live log was `cli`,
# every one labelled `cli`, three of them stamped within two seconds of one cold
# boot while only TWO watch_inbox hook events were visible in the session. The
# instrument could not discriminate the axis it was built for - which hook, on
# which event, and does SessionStart survive `/clear`.
#
# AN ARM ON `resolve_source`'s RETURN VALUE PROVES NOTHING ABOUT THIS. A gate
# tested as a pure predicate is not an enforced gate, and that has recurred four
# times in this tree. So the arms below parse the REAL settings file and read
# the label off the REAL declared command, and one of them fires that command
# and reads the entry-point column back off disk.
# ---------------------------------------------------------------------------


def _declared_source(command: str) -> str | None:
    """The `--source` label a declared hook command carries, if any.

    Read with the WATCHER'S OWN SCANNER over the command's tokens, not with a
    regex written here. Two readers of one argv reaching two answers is the
    defect this whole section is about, and the scanner is the reader that
    actually runs at the process entry point.
    """
    watcher = _watcher_module()
    return watcher.source_from_argv(_tokens(command)[1:])


def _watcher_hooks() -> list[HookCommand]:
    return [
        hook
        for hook in _hook_commands(_load_settings())
        if WATCHER in _repo_relative_command(hook.command)
    ]


def test_every_declared_watcher_hook_names_its_own_entry_point():
    """THE DECLARATION HALF. Read off the tracked settings file, not a fixture.

    DISCOVERED FROM THE WATCHER, NEVER LISTED HERE. The event-to-label mapping
    lives in `scripts/watch_inbox.py` as `HOOK_EVENT_SOURCES`, so an event wired
    tomorrow inherits this arm rather than needing somebody to remember it, and
    a label renamed in the script turns this red instead of drifting.
    """
    watcher = _watcher_module()
    hooks = _watcher_hooks()
    assert len(hooks) >= 2, (
        f"only {len(hooks)} declared hook(s) run {WATCHER}; the whole question is "
        "whether two different events can be told apart, and one event cannot "
        "make this arm mean anything"
    )

    for hook in hooks:
        expected = watcher.HOOK_EVENT_SOURCES.get(hook.event)
        assert expected is not None, (
            f"hooks.{hook.event} runs {WATCHER} but the watcher declares no label "
            f"for that event. Add it to HOOK_EVENT_SOURCES: it knows "
            f"{sorted(watcher.HOOK_EVENT_SOURCES)}"
        )
        assert _declared_source(hook.command) == expected, (
            f"hooks.{hook.event} declares `{hook.command}`, which labels itself "
            f"{_declared_source(hook.command)!r} rather than {expected!r}. Without "
            f"it the fire lands in the log as {watcher.SOURCE_CLI!r}, exactly like "
            "every other caller of this script"
        )


def test_no_two_hook_events_share_one_entry_point_label():
    """THE PROPERTY, stated without naming an event.

    Two events writing one label is the state this work exists to leave, and it
    is not caught by checking each event against its own expectation - a copied
    mapping entry satisfies that and still collapses the column.
    """
    labels = {hook.event: _declared_source(hook.command) for hook in _watcher_hooks()}
    assert len(labels) >= 2, f"only {len(labels)} event(s) run the watcher: {labels}"
    assert None not in labels.values(), f"an event declares no label at all: {labels}"
    assert len(set(labels.values())) == len(labels), (
        f"two hook events write the same entry-point label: {labels}. The log then "
        "answers 'something fired' and the question is WHICH hook fired"
    )


def test_the_declared_labels_are_not_the_fallback_every_caller_writes():
    """NON-VACUITY. `cli` in a hook command would satisfy every arm above.

    It would parse, it would be distinct from nothing, and it would leave the
    log exactly as unreadable as it was - which is the shape a mapping filled
    in without reading this section would take.
    """
    watcher = _watcher_module()
    declared = {_declared_source(hook.command) for hook in _watcher_hooks()}
    assert declared, "no declared label to grade"
    for label in declared:
        assert label not in (watcher.SOURCE_CLI, watcher.SOURCE_SUITE, watcher.SOURCE_MAIN), (
            f"a hook declares {label!r}, which is the label a bare run, this suite "
            "or an in-process call already writes; the fire stays unseparable"
        )


def test_the_declared_source_flag_is_still_a_relative_machine_neutral_command():
    """The new token must not have smuggled anything machine-specific in.

    A sibling's `.claude/settings.json` carried eleven hardcoded `C:\\Users\\`
    paths. The absolute-path guard already sweeps every token, and this arm
    states the narrower fact for the token this work added, so a label like
    `C:/x` would be red here as well as there.
    """
    watcher = _watcher_module()
    for hook in _watcher_hooks():
        tokens = _tokens(hook.command)
        assert watcher.SOURCE_FLAG in tokens, (
            f"hooks.{hook.event} carries no {watcher.SOURCE_FLAG} token: {hook.command!r}"
        )
        assert WATCHER in [_repo_relative(token) for token in tokens], (
            f"hooks.{hook.event} no longer names {WATCHER} as a relative path: "
            f"{hook.command!r}"
        )
        for token in tokens:
            assert not _is_absolute(_repo_relative(token)), (
                f"hooks.{hook.event} pins itself to one machine: {token!r}"
            )


def test_a_fired_hook_writes_its_declared_label_on_both_lines(tmp_path):
    """THE ENFORCED-GATE ARM. Fire the declared command, read the column back.

    BOTH LINES, AND THAT IS THE POINT. `main` writes its `start` line BEFORE
    `_main` parses argv, so a label resolved by argparse alone would appear on
    the terminal line only and the two lines of one fire would name two
    different callers. A fire killed at the hook's five second ceiling writes
    only the `start` line, which would then be the unlabelled one - the exact
    case the log exists to catch.

    `RESINCOMPUTE_INVOCATION_SOURCE` IS UNSET FOR THIS ARM ALONE, because it
    outranks the flag by design and leaving it set would make this a statement
    about the variable rather than about the declared command. The runtime
    redirect stays, so nothing here can reach `ops/runtime/` -
    `test_this_file_stamps_nothing_into_the_live_runtime_records` is what
    holds that claim rather than this comment.
    """
    hooks = _watcher_hooks()
    assert len(hooks) >= 2, f"only {len(hooks)} declared watcher hook(s) to fire"

    observed: dict[str, set[str]] = {}
    for index, hook in enumerate(hooks):
        fired = _fire(_argv(hook.command), tmp_path, f"entrypoint-{index}", source=None)
        assert fired.status == 0, (
            f"`{hook.command}` exited {fired.status}; a label the parser rejects "
            f"fails on EVERY fire. stderr: {fired.noise.strip()[:400]!r}"
        )
        assert fired.runtime is not None

        lines = _isolated_lines(fired.runtime)
        phases = [line.split("\t")[-1] for line in lines]
        assert len(lines) == 2 and _watcher_module().PHASE_START in phases, (
            f"`{hook.command}` left {phases}, not a start and one terminal, so the "
            "two-line property this arm grades is not present to grade"
        )
        sources = {line.split("\t")[1] for line in lines}
        assert sources == {_declared_source(hook.command)}, (
            f"`{hook.command}` wrote {sources} but declares "
            f"{_declared_source(hook.command)!r}. If the two lines disagree the "
            "start line is being labelled before argv is read, which is the trap"
        )
        observed[hook.event] = sources

    distinct = {label for sources in observed.values() for label in sources}
    assert len(distinct) == len(observed), (
        f"the fires were not separable on disk: {observed}. This is the arm that "
        "would have caught the state at HEAD 0e9491a, where every fire from "
        "three different callers all read `cli`"
    )
