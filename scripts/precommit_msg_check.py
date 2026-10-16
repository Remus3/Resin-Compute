"""scripts/precommit_msg_check.py - commit-msg hook (Conventional Commits).

Validates the commit's SUBJECT line against the Conventional Commits shape:
`<type>(<scope>)?!?: <description>`. Body and trailers are unrestricted.

Auto-generated subjects (Merge / Revert / Reapply / fixup! / squash! / amend!)
are skipped - git writes those itself and rejecting them would break a rebase.
The one exception: a merge subject (`merge: <topic>`, the authored template,
or git's `Merge ...`) is rejected when it names a worktree or agent - see
MERGE SUBJECTS below.

Runs LAST in .githooks/commit-msg, after the trailer strip and the glyph gate,
so it validates the message that will actually be committed rather than a
draft of it.

`#` LINES ARE CONTENT UNLESS GIT PROVABLY STRIPS THEM. Git runs commit-msg on
the PRE-cleanup bytes, and `git commit -F` / `-m` default to cleanup=whitespace,
which keeps `#` lines - so a `#` first line IS the landed subject there.
Measured 2026-10-03; `hash_lines_are_stripped` holds the decision and the
measured table. Every unknown fails closed, with one exception.

AN EXPLICIT `--cleanup=` FLAG on an EDITOR commit is read from git's own
template, not guessed. Git passes no flag to the hook, but it writes its
EFFECTIVE cleanup mode into the editor template in the very file the hook is
handed: "will be ignored" under strip, "will be kept" under whitespace and
verbatim. `.githooks/commit-msg` exports that file's path as
`RESIN_COMMIT_MSG_FILE`, and only the commit template's exact two-line strip
sentence, with no keep sentence beside it, lets `#` lines be skipped.

RESIDUALS, each measured or reasoned in `hash_lines_are_stripped`:
`-F`/`-m` with `commit.cleanup=strip` in config AND an explicit
`--cleanup=whitespace|verbatim` on the command line (no template, flag
invisible) still skips `#` lines that land; a human who deletes git's keep
sentence and types its strip sentence defeats the read on purpose. A
localised git that translates the sentence reads as "unknown" and fails
closed, which can falsely block a non-ASCII branch or path in its template.

Bypass with `--no-verify` if absolutely necessary; please do not make a habit
of it.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

TYPES = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)

# <type>(<optional scope>)<optional !>: <space><non-space>...
SUBJECT_RE = re.compile(
    rf"^(?:{'|'.join(TYPES)})(?:\([\w./\- ]+\))?!?:\s+\S",
)

SKIP_PREFIXES = (
    "Merge ",
    "Revert ",
    "Reapply ",
    "fixup!",
    "squash!",
    "amend!",
)

SOFT_LINE_LIMIT = 100

# MERGE SUBJECTS (MAIN ORDER 1925 item b). The authored merge template is
# `merge: <topic>`; it replaces the old `Merge slice ...` form, which this check
# used to force by rejecting `merge:` outright. `merge:` is legal ONLY on a
# real merge commit - a merge in progress, read from MERGE_HEAD by the hook
# entry point and passed in, so `validate` stays pure. On any other commit it
# is rejected exactly as before.
#
# A merge commit's subject never carries a worktree or agent ID. Refute round 1
# narrowed the shapes to real ids: harness agent ids are 17 hex digits, so
# `agent-<15+ hex>`; `worktree-agent-<hex>` branches; any `.claude/worktrees`
# path; and a live linked worktree's branch or directory name ONLY when it
# carries a 6+ hex run. Topic words such as `worktree-cleanup`, `agent-facade`
# or a worktree named `lane` never block. Non-merge subjects are not swept:
# `fix(worktree-cleanup): ...` is about worktrees, not a leak of one.
MERGE_SUBJECT_RE = re.compile(r"^merge:\s+\S")
MERGE_TEMPLATE = "merge: <topic>"

WORKTREE_NAME_PATTERNS = (
    re.compile(r"(?<![0-9a-z])worktree-agent-[0-9a-f]+", re.IGNORECASE),
    re.compile(r"(?<![0-9a-z])agent-[0-9a-f]{15,}(?![0-9a-z])", re.IGNORECASE),
    re.compile(r"\.claude[/\\]+worktrees", re.IGNORECASE),
)

#: A live worktree name is treated as an id only when it carries this.
_HEX_RUN = re.compile(r"[0-9a-f]{6,}", re.IGNORECASE)


def _parse_worktree_porcelain(text: str) -> tuple[str, ...]:
    """Branch short names and directory basenames of every LINKED worktree in
    `git worktree list --porcelain` output. The first entry is the main
    checkout and is skipped: its branch (`main`) is the merge target, not a
    worktree name."""
    names: list[str] = []
    for index, block in enumerate(text.replace("\r\n", "\n").split("\n\n")):
        if index == 0:
            continue
        for line in block.splitlines():
            if line.startswith("worktree "):
                base = re.split(r"[/\\]", line[len("worktree ") :].rstrip("/\\"))[-1]
                if base:
                    names.append(base)
            elif line.startswith("branch "):
                ref = line[len("branch ") :].strip()
                short = ref[len("refs/heads/") :] if ref.startswith("refs/heads/") else ref
                if short:
                    names.append(short)
    return tuple(dict.fromkeys(names))


def _git_stdout(*args: str) -> str | None:
    """stdout of `git <args>`, or None when git could not answer."""
    try:
        proc = subprocess.run(
            ["git", *args],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace")


def linked_worktree_names() -> tuple[str, ...]:
    """Live names of this repo's linked worktrees.

    ADDITIVE, not the floor: `WORKTREE_NAME_PATTERNS` reject every agent and
    worktree-agent shape with no git call at all. A git that cannot answer
    yields no extra names rather than a refusal - failing closed here would
    block every merge commit over a listing problem unrelated to its subject.
    """
    out = _git_stdout("worktree", "list", "--porcelain")
    return () if out is None else _parse_worktree_porcelain(out)


def _merge_head_path() -> str | None:
    out = _git_stdout("rev-parse", "--git-path", "MERGE_HEAD")
    return None if out is None else out.strip() or None


def merge_in_progress(path_of_merge_head: Callable[[], str | None] | None = None) -> bool:
    """True when MERGE_HEAD exists, i.e. this commit is a merge commit.

    `git rev-parse --git-path MERGE_HEAD` resolves the per-worktree git dir,
    so a linked worktree reads its own merge state. A git that cannot answer
    reads as NOT a merge, which fails closed for `merge:`: it is rejected.
    """
    path = (path_of_merge_head or _merge_head_path)()
    return path is not None and Path(path).is_file()


def head_is_merge() -> bool:
    """True iff HEAD has a second parent (`git rev-parse --verify -q HEAD^2`).

    Refute round 2, ruling C: `git commit --amend` of a merge commit runs
    commit-msg with no MERGE_HEAD, so MERGE_HEAD alone refused a legitimate
    amend. False on any failure, an unborn HEAD included.

    RESIDUAL, accepted by the ruling and pinned by a test: a NEW non-merge
    commit made directly on top of a merge also sees HEAD^2, so it may carry
    a `merge:` subject. The worktree-name leak check is unaffected.
    """
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", "-q", "HEAD^2"],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def _worktree_name_in(subject: str, worktree_names: tuple[str, ...]) -> str | None:
    for pattern in WORKTREE_NAME_PATTERNS:
        match = pattern.search(subject)
        if match:
            return match.group(0)
    for name in worktree_names:
        if not _HEX_RUN.search(name):
            continue
        if re.search(rf"(?<![\w./-]){re.escape(name)}(?![\w./-])", subject, re.IGNORECASE):
            return name
    return None


def validate(
    subject: str,
    *,
    merge_in_progress: bool = False,
    worktree_names: tuple[str, ...] = (),
    head_is_merge: bool = False,
) -> tuple[bool, str | None]:
    """Return (ok, error_message). error_message is None on success.

    Pure: the hook entry point reads `merge_in_progress` (MERGE_HEAD),
    `head_is_merge` (HEAD^2) and the live `worktree_names` and passes them in.
    `head_is_merge` admits `merge:` only; it never widens the leak check.
    """
    if not subject.strip():
        return False, "empty subject line"
    merge_form = subject.startswith("Merge ") or subject.startswith("merge:")
    if merge_in_progress or merge_form:
        leaked = _worktree_name_in(subject, worktree_names)
        if leaked is not None:
            return False, (
                f"merge subject names a worktree or agent ({leaked!r}); "
                f"write {MERGE_TEMPLATE} with no worktree, agent or branch name"
            )
    if subject.startswith("merge:"):
        if not (merge_in_progress or head_is_merge):
            return False, (
                f"{MERGE_TEMPLATE} is only for a merge commit, and no merge is in "
                "progress (no MERGE_HEAD) nor is HEAD a merge"
            )
        if MERGE_SUBJECT_RE.match(subject):
            return True, None
        return False, f"merge subject has no topic; write {MERGE_TEMPLATE}"
    if any(subject.startswith(p) for p in SKIP_PREFIXES):
        return True, None
    if not SUBJECT_RE.match(subject):
        return False, "subject does not match <type>(<scope>)?: <description>"
    return True, None


class ConfigUnreadable(RuntimeError):
    """git could not answer a config question. Never read as "unset"."""


def _git_config_get(key: str) -> str | None:
    """The value of `key`, None when git positively answers it is unset.

    `git config --get` exits 1 for an absent key; anything else non-zero, or a
    git that cannot be run, raises - "could not check" is not "unset".
    """
    try:
        proc = subprocess.run(
            ["git", "config", "--get", key],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigUnreadable(key) from exc
    if proc.returncode == 1:
        return None
    if proc.returncode != 0:
        raise ConfigUnreadable(key)
    return proc.stdout.decode("utf-8", "replace").strip()


# Git's editor template, byte-exact from git 2.53.0.windows.3, measured
# 2026-10-03 (the wrap is inside git's own translatable string, not ours). Only
# `git commit` writes these; `git merge --edit` writes its own text, which says
# "ignored" in EVERY cleanup mode, verbatim included - so it is not a signal.
TEMPLATE_STRIP_HINT = (
    "# Please enter the commit message for your changes. Lines starting",
    "# with '#' will be ignored, and an empty message aborts the commit.",
)
TEMPLATE_KEEP_HINT = (
    "# Please enter the commit message for your changes. Lines starting",
    "# with '#' will be kept; you may remove them yourself if you want to.",
)

#: Exported by `.githooks/commit-msg` as the path git handed the hook.
MESSAGE_FILE_ENV = "RESIN_COMMIT_MSG_FILE"


def _has_pair(lines: list[str], pair: tuple[str, str]) -> bool:
    return any(
        lines[i] == pair[0] and lines[i + 1] == pair[1] for i in range(len(lines) - 1)
    )


def template_says_stripped(message: str) -> bool | None:
    """What git's OWN editor template says about `#` lines in this message.

    True for the strip sentence, False for the keep sentence, None when
    neither is there (`--no-status`, scissors, a merge, a localised git, a
    template the author deleted). The keep sentence wins over the strip one: an
    amend can carry an old landed strip sentence above a new keep sentence.
    """
    lines = message.splitlines()
    if _has_pair(lines, TEMPLATE_KEEP_HINT):
        return False
    if _has_pair(lines, TEMPLATE_STRIP_HINT):
        return True
    return None


def _message_from_env(env: Mapping[str, str]) -> str | None:
    path = env.get(MESSAGE_FILE_ENV)
    if not path:
        return None
    try:
        return Path(path).read_bytes().decode("utf-8", "replace")
    except OSError:
        return None


def hash_lines_are_stripped(
    env: Mapping[str, str] | None = None,
    config_get: Callable[[str], str | None] | None = None,
    message: str | None = None,
) -> bool:
    """True only when git provably strips `#` lines from THIS commit.

    MEASURED 2026-10-03 on git 2.53.0.windows.3: commit-msg is handed the
    PRE-cleanup bytes in every mode, the editor flow included. `-F` and `-m`
    default to cleanup=whitespace and KEEP `#` lines; the editor flow defaults
    to cleanup=strip. `GIT_EDITOR=:` is exported exactly when no editor was
    used, and `GIT_INDEX_FILE` to every commit hook.

    NO EDITOR: `commit.cleanup` decides. A `--cleanup=` flag here is
    INVISIBLE - no template is written - so `-F --cleanup=verbatim` under a
    configured `strip` is the residual named in the module docstring.

    EDITOR: git's template decides, never the config, because the template
    carries the EFFECTIVE mode with any `--cleanup=` flag applied. `message`
    is the hook's message text; when None it is read from the path in
    `RESIN_COMMIT_MSG_FILE`. Only the strip sentence answers True.

    Fails CLOSED - False, so `#` lines are judged as content - whenever the
    answer is not known: outside a commit hook, a config git cannot read, an
    unknown cleanup mode, a comment character other than `#`, or an editor
    commit whose template does not carry the strip sentence.
    """
    env = os.environ if env is None else env
    config_get = _git_config_get if config_get is None else config_get
    if "GIT_INDEX_FILE" not in env:
        return False
    editor_used = env.get("GIT_EDITOR") != ":"
    try:
        for key in ("core.commentString", "core.commentChar"):
            value = config_get(key)
            if value is not None and value != "#":
                return False
        if editor_used:
            if message is None:
                message = _message_from_env(env)
            return message is not None and template_says_stripped(message) is True
        mode = (config_get("commit.cleanup") or "default").strip().lower()
    except ConfigUnreadable:
        return False
    # Without an editor the default IS whitespace. whitespace, verbatim and
    # scissors KEEP `#` lines - scissors truncates at its marker line and keeps
    # every `#` line above it. Anything else is unknown: fail closed.
    return mode == "strip"


def _read_subject(msg_file: Path, *, hash_is_content: bool = True) -> str:
    """The first line git will keep: the first non-blank line, skipping `#`
    lines only when the caller has shown git strips them. Default: content."""
    raw = msg_file.read_text(encoding="utf-8", errors="replace")
    for line in raw.splitlines():
        if not hash_is_content and line.startswith("#"):
            continue
        if not line.strip():
            continue
        return line.rstrip()
    return ""


def main() -> int:
    if len(sys.argv) < 2:
        print("commit-msg: missing path argument", file=sys.stderr)
        return 1
    msg_file = Path(sys.argv[1])
    if not msg_file.exists():
        print(f"commit-msg: file not found: {msg_file}", file=sys.stderr)
        return 1

    message = msg_file.read_bytes().decode("utf-8", "replace")
    subject = _read_subject(
        msg_file, hash_is_content=not hash_lines_are_stripped(message=message)
    )
    merging = merge_in_progress()
    names = linked_worktree_names() if merging or subject.startswith(("Merge ", "merge:")) else ()
    head_merge = head_is_merge() if subject.startswith("merge:") and not merging else False
    ok, err = validate(
        subject, merge_in_progress=merging, worktree_names=names, head_is_merge=head_merge
    )
    if not ok:
        print(
            "commit-msg: subject line rejected.\n"
            f"  reason:   {err}\n"
            f"  got:      {subject!r}\n"
            "  expected: <type>(<scope>)?: <description>\n"
            f"  types:    {', '.join(TYPES)}\n"
            "  example:  feat(engine): add weapon-banner fate point carry\n"
            f"  merges:   {MERGE_TEMPLATE} - never a worktree, agent or branch name\n"
            "  example:  merge: P3 merge subject template\n"
            "Bypass with --no-verify if absolutely necessary.",
            file=sys.stderr,
        )
        return 1

    if len(subject) > SOFT_LINE_LIMIT:
        # Warn-only: nudge, do not block.
        print(
            f"commit-msg: subject is {len(subject)} chars (>{SOFT_LINE_LIMIT}); "
            "consider tightening.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
