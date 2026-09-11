"""A document that QUOTES a hook command must quote the live declaration.

WHY THIS EXISTS, AND IT IS NOT HYPOTHETICAL.

Commit 3964544 added a `--source` flag to two of the hook commands in
`.claude/settings.json` so a fired hook names itself in the invocation log.
`tests/test_session_hooks.py` grades the settings file. `tests/test_docs_consistency.py`
grades the docs against the TREE - it asks whether a cited path resolves and
whether git stores it. Nothing in this tree graded a DOCUMENT against the
settings file, so `docs/INBOX_TRIAGE_2026-09-07-0710.md` went on reproducing the
pre-3964544 command strings, in a sentence whose whole job was to enumerate what
the settings file declares. The doc was not wrong when it was written. It became
wrong when the declaration moved and nothing connected the two.

THE DECLARATION IS PARSED, NEVER RESTATED.

Every command string this file compares against is read out of
`.claude/settings.json` as JSON at run time. Not one of them is spelled here.
A guard that carried its own copy of the truth would go stale by exactly the
mechanism it exists to catch, and would then certify the stale doc.

SCOPE: EVERY TRACKED `.md`, NARROWED BY A PROPERTY OF THE CITATION.

Not a named list of documents. A named list is a second thing to keep in sync,
and the next triage note somebody writes would not be on it. `git ls-files` is
the corpus, matching the sweep discipline in `tests/test_docs_consistency.py`.

The narrowing is done by asking what a citation IS, not where it lives. A
backticked command is treated as a QUOTATION OF THE DECLARATION, and therefore
graded, when either:

  (a) it carries a long flag. A bare `python <script>` is how a reader is told
      to run the script by hand, and both `CLAUDE.md` and `ROADMAP.md` use it
      that way correctly. The moment a document reproduces the FLAGS it has
      stopped describing the script and started transcribing the declaration.

  (b) the claim-block it sits in names the settings file. A sentence that says
      "the settings file registers X" is asserting what the settings file
      contains, whether or not it bothered with the flags.

A CLAIM-BLOCK IS A MARKDOWN STRUCTURE, NOT A LINE WINDOW.

A blank-line paragraph, split further at each list-item bullet. A tuned
line-distance would be fitted to today's corpus and would read as evidence
without being any. A list item is a unit of claim: `CLAUDE.md` names the
settings file in one bullet and invokes the watcher by hand in another, several
bullets later, and those are two separate assertions that happen to share a
paragraph because markdown lists are not blank-line separated.

FENCED CODE BLOCKS ARE STRIPPED FIRST, AND THAT IS LOAD-BEARING.

Inline-code pairing is positional. A ``` fence is an ODD run of backticks, so
scanning past one pairs the closing backtick of one span with the opening
backtick of the next and yields tokens that exist nowhere in the document.
Measured while writing this file: an unstripped scan of `.claude/commands/done.md`
produced a single fused token spanning three separate code spans. The stripper
replaces fenced lines with empty ones rather than deleting them, so reported
line numbers still point at the real line.

EVERY CHECKER RETURNS A PAIR - `(checked, offenders)` - and every arm asserts
the checked count before it asserts the offender list, the convention
`tests/test_session_hooks.py` established after a sibling project shipped a
hook checker that reported zero missing out of zero examined and read as green
in four repositories. Zero out of zero is not a pass.

EVERY SWEEP CARRIES TWO GUARDS. One says the stale quote is caught; its partner
says an exact quote and a legitimate bare invocation both SURVIVE. A detector
that flagged every command would pass the first arm of every pair while telling
the reader nothing true. The mutation arms drive the checkers with planted text
built in memory - nothing here writes to the tree, because a break-revert-observe
cycle on a tracked file is how a parallel agent turns somebody else's suite red
while they are measuring it.
"""
from __future__ import annotations

import functools
import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS = REPO_ROOT / ".claude" / "settings.json"

#: How the settings file is spelled when a document cites it. Derived from the
#: path this module already has to know in order to READ the file, so it is the
#: same constant rather than a second copy of anything.
SETTINGS_CITATION = SETTINGS.relative_to(REPO_ROOT).as_posix()

#: A line that opens or closes a fenced code block.
_FENCE = re.compile(r"^\s*(?:```|~~~)")

#: A line that starts a markdown list item, at any indent. Ordered and
#: unordered alike, both common ordered spellings.
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")

#: An inline code span. `re.DOTALL` on purpose: a hard-wrapped document splits a
#: long command across a line break inside the backticks, which is exactly how
#: the stale quote at the bottom of the triage note was spelled, and a pattern
#: that stopped at the newline would have walked straight past it.
_CODE_SPAN = re.compile(r"`([^`]+)`", re.DOTALL)


@dataclass(frozen=True)
class Citation:
    """One backticked command found in a document."""

    document: str
    line: int
    command: str
    has_long_flag: bool
    block_cites_settings: bool
    #: Non-empty when shlex could not split this span. APPENDED at the end of
    #: the field list with a default, per this tree's dataclass rule: a
    #: mid-class required field breaks every existing positional construction.
    unparse_reason: str = ""

    @property
    def in_scope(self) -> bool:
        return self.has_long_flag or self.block_cites_settings or bool(self.unparse_reason)

    def __str__(self) -> str:
        suffix = f" [UNPARSEABLE: {self.unparse_reason}]" if self.unparse_reason else ""
        return f"{self.document}:{self.line}: {self.command}{suffix}"


# ---------------------------------------------------------------------------
# Reading the declaration - always from the real file, never restated
# ---------------------------------------------------------------------------


def _tokens(command: str) -> list[str]:
    """The command split the way a shell would, surrounding quotes removed.

    `posix=False` for the reason `tests/test_session_hooks.py` records: in POSIX
    mode shlex eats a backslash as an escape, so a Windows-spelled path would
    arrive with its separators silently deleted.

    RAISES `UnparseableCommand` - defined at the END of this module - rather than
    answering `[]`. See that class for the defect the empty answer certified.
    """
    try:
        return [token.strip("\"'") for token in shlex.split(command, posix=False)]
    except ValueError as exc:
        raise UnparseableCommand(_unparseable_reason(command, exc)) from exc


def _normalise(command: str) -> str:
    """Collapse every run of whitespace, including the newline a hard wrap adds."""
    return " ".join(command.split())


@functools.lru_cache(maxsize=1)
def _declared_commands() -> tuple[str, ...]:
    """Every `type: command` hook string in the live settings file, normalised.

    FAILS rather than skips when the file is absent. A skip would be the
    zero-out-of-zero result this file exists to refuse.
    """
    assert SETTINGS.is_file(), (
        f"{SETTINGS_CITATION} does not exist, so there is no declaration to grade "
        "the documents against. This guard FAILS rather than skips: a skip here "
        "is a checker that examined nothing reporting a clean bill of health."
    )
    payload = json.loads(SETTINGS.read_bytes().decode("utf-8"))
    assert isinstance(payload, dict), f"{SETTINGS_CITATION} parses to {type(payload).__name__}, not an object"

    hooks = payload.get("hooks")
    assert isinstance(hooks, dict), f"{SETTINGS_CITATION} declares no `hooks` object"

    found: list[str] = []
    for event in sorted(hooks):
        groups = hooks[event]
        assert isinstance(groups, list), f"hooks.{event} is {type(groups).__name__}, not a list"
        for group in groups:
            assert isinstance(group, dict), f"hooks.{event} holds a {type(group).__name__}, not an object"
            entries = group.get("hooks", [])
            assert isinstance(entries, list), f"hooks.{event}[].hooks is {type(entries).__name__}, not a list"
            for entry in entries:
                assert isinstance(entry, dict), f"hooks.{event}[].hooks holds a {type(entry).__name__}"
                if entry.get("type") != "command":
                    continue
                command = entry.get("command")
                assert isinstance(command, str) and command.strip(), (
                    f"hooks.{event} declares a command hook with no command string"
                )
                found.append(_normalise(command))
    return tuple(found)


def _declared_scripts(commands: tuple[str, ...]) -> frozenset[str]:
    """The `.py` targets the declaration invokes.

    A document command is only compared against the declaration when it names
    one of these. Anything else is some other script and none of this file's
    business - `python scripts/install_hooks.py` in `CLAUDE.md` is a real
    instruction to a reader and is not a hook declaration.
    """
    return frozenset(token for command in commands for token in _tokens(command) if token.endswith(".py"))


# ---------------------------------------------------------------------------
# Reading the documents
# ---------------------------------------------------------------------------


def _strip_fences(text: str) -> str:
    """Blank out fenced code blocks, PRESERVING the line count.

    Blanked rather than removed so a reported line number still points at the
    line a reader will open. See this module's docstring for the pairing
    desync a fence causes when it is left in.
    """
    out: list[str] = []
    inside = False
    for line in text.split("\n"):
        if _FENCE.match(line):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return "\n".join(out)


def _claim_blocks(text: str) -> list[tuple[int, str]]:
    """`(start offset, block text)` for each unit of claim in the document.

    A blank line ends a block, and so does the start of a list item. The second
    rule is what keeps two unrelated bullets of one markdown list from being
    read as a single assertion.
    """
    blocks: list[tuple[int, str]] = []
    start = 0
    current: list[str] = []
    offset = 0

    def flush() -> None:
        if any(line.strip() for line in current):
            blocks.append((start, "\n".join(current)))
        current.clear()

    for line in text.split("\n"):
        breaks = not line.strip() or _BULLET.match(line)
        if breaks and current:
            flush()
            start = offset
        if not line.strip():
            start = offset + len(line) + 1
        else:
            if not current:
                start = offset
            current.append(line)
        offset += len(line) + 1
    flush()
    return blocks


def _citations(document: str, text: str, scripts: frozenset[str]) -> list[Citation]:
    """Every backticked command in `text` that invokes a declared hook script."""
    stripped = _strip_fences(text)
    found: list[Citation] = []
    for block_start, block in _claim_blocks(stripped):
        cites_settings = SETTINGS_CITATION in block
        for match in _CODE_SPAN.finditer(block):
            command = _normalise(match.group(1))
            tokens, unparse_reason = _scope_tokens(command, scripts)
            # A COMMAND, NOT A PATH. `scripts/watch_inbox.py` on its own is a
            # pointer at a file and belongs to `tests/test_docs_consistency.py`,
            # which resolves it against the tree. It becomes this file's
            # business only when something INVOKES it - when the declared script
            # appears after a leading interpreter token. Grading bare pointers
            # was this file's first draft, and it demanded edits to `ROADMAP.md`
            # and `docs/LEDGER.md` for citations that were never wrong.
            if not any(token in scripts for token in tokens[1:]):
                continue
            absolute = block_start + match.start()
            found.append(
                Citation(
                    document=document,
                    line=stripped[:absolute].count("\n") + 1,
                    command=command,
                    has_long_flag=any(token.startswith("--") for token in tokens),
                    block_cites_settings=cites_settings,
                    unparse_reason=unparse_reason,
                )
            )
    return found


def _check(document: str, text: str, commands: tuple[str, ...]) -> tuple[int, list[str]]:
    """`(citations graded, the ones that no longer match the declaration)`."""
    scripts = _declared_scripts(commands)
    graded = [c for c in _citations(document, text, scripts) if c.in_scope]
    offenders = [str(c) for c in graded if c.command not in commands]
    return len(graded), offenders


@functools.lru_cache(maxsize=1)
def _tracked_markdown() -> tuple[Path, ...]:
    """Every `.md` git stores, read from the index rather than walked on disk.

    The index, not a `rglob`: a nested checkout or a sibling worktree left under
    this tree is somebody else's documentation and its quotations are not this
    tree's to grade. `tests/test_guard_worktree_exclusion.py` carries the
    measurement behind that rule.

    `-z` avoids core.quotePath escaping, which mangles any non-ASCII path into a
    quoted form that no longer names a real file.
    """
    require_git_repository()
    completed = subprocess.run(
        ["git", "ls-files", "-z", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return tuple(REPO_ROOT / entry for entry in completed.stdout.split("\0") if entry)


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_every_quoted_hook_command_matches_the_live_declaration():
    """The arm that would have caught the triage note on the day 3964544 landed."""
    commands = _declared_commands()
    checked = 0
    offenders: list[str] = []
    for path in _tracked_markdown():
        if not path.is_file():
            continue
        document = path.relative_to(REPO_ROOT).as_posix()
        count, bad = _check(document, path.read_text(encoding="utf-8"), commands)
        checked += count
        offenders.extend(bad)

    assert checked, (
        "no document quotes a declared hook command at all, so the sweep above "
        "proves nothing. Either the citation parser broke or the settings file "
        "stopped being cited anywhere."
    )
    assert not offenders, (
        "these documents quote a hook command that "
        f"{SETTINGS_CITATION} no longer declares - the live declaration is "
        f"{list(commands)}: " + "; ".join(sorted(offenders))
    )


# ---------------------------------------------------------------------------
# Non-vacuity: the declaration really was read, and read from the real file
# ---------------------------------------------------------------------------


def test_the_declaration_is_read_from_the_live_settings_file():
    """Not a fixture, not a restatement - the file the hooks are declared in."""
    assert SETTINGS.is_file(), f"{SETTINGS_CITATION} is missing"
    commands = _declared_commands()
    assert commands, "the settings file declares no command hook at all"
    assert set(commands) <= set(_normalise(c) for c in re.findall(r'"command"\s*:\s*"([^"]*)"', SETTINGS.read_text(encoding="utf-8"))), (
        "a command reached the checker that is not a `command` string in the settings file"
    )
    scripts = _declared_scripts(commands)
    assert scripts, "no declared hook command invokes a .py target, so nothing can ever be in scope"
    for script in scripts:
        assert (REPO_ROOT / script).is_file(), f"the declaration invokes {script}, which is not here"


def test_at_least_one_declared_command_carries_a_long_flag():
    """Otherwise trigger (a) is dead weight and only the settings-citation
    trigger does any work. This asserts the PROPERTY, never a count and never a
    flag spelling - both of those move, and a number baked in here would be
    stale within the hour."""
    flagged = [c for c in _declared_commands() if any(t.startswith("--") for t in _tokens(c))]
    assert flagged, "no declared hook command carries a long flag"


def test_the_sweep_walked_a_real_corpus():
    """A parser that recognised nothing would make the gate vacuous."""
    documents = _tracked_markdown()
    assert len(documents) >= 10, f"git stores only {len(documents)} markdown files - wrong cwd, or not a checkout"
    scripts = _declared_scripts(_declared_commands())
    seen = 0
    for path in documents:
        if path.is_file():
            seen += len(_citations(path.relative_to(REPO_ROOT).as_posix(), path.read_text(encoding="utf-8"), scripts))
    assert seen, "the citation parser found no hook-command quotation anywhere in the tree"


# ---------------------------------------------------------------------------
# Non-vacuity: the detector fires, and its legitimate neighbours survive
#
# Every arm below drives the checkers with text built in memory. Nothing here
# touches a tracked file.
# ---------------------------------------------------------------------------


def _a_declared_command() -> str:
    """A live declared command that carries a long flag, for the planted arms."""
    for command in _declared_commands():
        if any(t.startswith("--") for t in _tokens(command)):
            return command
    raise AssertionError("no declared hook command carries a long flag")


def test_the_detector_fires_on_a_flag_that_the_declaration_dropped():
    """A quotation missing a flag the declaration carries is the real defect."""
    live = _a_declared_command()
    truncated = " ".join(t for t in _tokens(live) if not t.startswith("--"))
    assert truncated != live, "the probe did not actually change the command"
    checked, offenders = _check("planted.md", f"a hook (`{truncated} --not-a-real-flag`).", _declared_commands())
    assert checked == 1, f"the probe was not graded at all: checked={checked}"
    assert offenders, "a command the declaration does not carry was waved through"


def test_the_detector_leaves_an_exact_quotation_alone():
    """The survival partner. A detector that flagged everything would pass the
    arm above while saying nothing true."""
    live = _a_declared_command()
    checked, offenders = _check("planted.md", f"the hook is `{live}` today.", _declared_commands())
    assert checked == 1, f"an exact quotation was not graded: checked={checked}"
    assert not offenders, f"an exact quotation was reported stale: {offenders}"


def test_a_quotation_survives_being_hard_wrapped_across_a_line():
    """The bottom of the triage note spelled its command across a line break
    inside the backticks. A parser that stopped at the newline walked past it."""
    live = _a_declared_command()
    tokens = _tokens(live)
    assert len(tokens) >= 2, "the live command is too short to wrap"
    wrapped = " ".join(tokens[:-1]) + "\n" + tokens[-1]
    checked, offenders = _check("planted.md", f"the hook is (`{wrapped}`).", _declared_commands())
    assert checked == 1, f"a hard-wrapped quotation was not graded: checked={checked}"
    assert not offenders, f"a hard-wrapped exact quotation was reported stale: {offenders}"


def test_a_bare_invocation_in_prose_is_not_graded():
    """`CLAUDE.md` and `ROADMAP.md` both tell a reader to run the watcher by
    hand. That is an instruction, not a transcription of the declaration, and
    grading it would make this file demand edits to documents that are correct."""
    script = sorted(_declared_scripts(_declared_commands()))[0]
    checked, offenders = _check("planted.md", f"run `python {script}` to see what is unread.", _declared_commands())
    assert checked == 0, "a bare invocation in prose was graded as a quotation"
    assert not offenders


def test_a_bare_invocation_beside_the_settings_file_is_graded():
    """The partner to the arm above, and the whole point of trigger (b): the
    same bare command becomes a claim once the sentence names the file it is
    claiming to reproduce."""
    script = sorted(_declared_scripts(_declared_commands()))[0]
    text = f"{SETTINGS_CITATION} registers `python {script}` as a hook."
    checked, offenders = _check("planted.md", text, _declared_commands())
    assert checked == 1, f"a claim about the settings file was not graded: checked={checked}"
    assert offenders, "an incomplete transcription of a declared command was waved through"


def test_a_bullet_ends_a_claim_block():
    """The discriminator's teeth. Two list items are two assertions even though
    markdown does not put a blank line between them - which is exactly how
    `CLAUDE.md` names the settings file in one bullet and invokes the watcher by
    hand in another."""
    script = sorted(_declared_scripts(_declared_commands()))[0]
    text = f"- a bullet naming {SETTINGS_CITATION} and nothing else.\n- another bullet: run `python {script}` by hand.\n"
    checked, offenders = _check("planted.md", text, _declared_commands())
    assert checked == 0, "a bare invocation in its own bullet was pulled into a neighbour's claim"
    assert not offenders

    fused = f"one paragraph naming {SETTINGS_CITATION} and also saying run `python {script}` by hand.\n"
    fused_checked, _ = _check("planted.md", fused, _declared_commands())
    assert fused_checked == 1, "the same two clauses in ONE block were not read as one claim - the splitter is inert"


def test_a_blank_line_ends_a_claim_block():
    script = sorted(_declared_scripts(_declared_commands()))[0]
    text = f"a paragraph naming {SETTINGS_CITATION}.\n\na later paragraph: run `python {script}` by hand.\n"
    checked, _ = _check("planted.md", text, _declared_commands())
    assert checked == 0, "a blank line failed to end the claim block"


def test_a_bare_path_pointer_is_not_a_command():
    """`docs/LEDGER.md` and `ROADMAP.md` cite the watcher BY PATH beside the
    settings file constantly. That is a pointer, graded by
    `tests/test_docs_consistency.py` against the tree, and it carries no flags
    to be stale about. The first draft of this file graded them and demanded
    edits to three documents whose citations were entirely correct."""
    script = sorted(_declared_scripts(_declared_commands()))[0]
    text = f"{SETTINGS_CITATION} wires `{script}` on every session start."
    checked, offenders = _check("planted.md", text, _declared_commands())
    assert checked == 0, "a bare path pointer was graded as a command quotation"
    assert not offenders

    # The survival partner: prefix an interpreter and it IS a command again, so
    # the narrowing above cannot have swallowed the real case.
    invoked = f"{SETTINGS_CITATION} wires `python {script}` on every session start."
    invoked_checked, invoked_bad = _check("planted.md", invoked, _declared_commands())
    assert invoked_checked == 1, "an invoked declared script was not graded - the narrowing went too far"
    assert invoked_bad, "an incomplete transcription of a declared command was waved through"


def test_a_command_for_some_other_script_is_out_of_scope():
    """Only the scripts the declaration actually invokes are graded. Otherwise
    every `python ... .py` in the docs becomes this file's business."""
    checked, offenders = _check(
        "planted.md",
        f"{SETTINGS_CITATION} exists; separately run `python scripts/install_hooks.py --force`.",
        _declared_commands(),
    )
    assert checked == 0, "a command for a script the declaration never invokes was graded"
    assert not offenders


# ---------------------------------------------------------------------------
# Non-vacuity: the fence stripper, and the desync it prevents
# ---------------------------------------------------------------------------


def test_the_fence_stripper_preserves_the_line_count():
    """A reported line number has to point at the line a reader will open."""
    text = "one\n```\ntwo\nthree\n```\nfour\n"
    assert _strip_fences(text).count("\n") == text.count("\n")
    assert _strip_fences(text).split("\n")[5] == "four"
    assert _strip_fences(text).split("\n")[2] == ""


def test_an_unstripped_fence_desyncs_the_pairing_and_the_stripper_fixes_it():
    """The positive control for the stripper, stated as the two results side by
    side rather than as a claim about one of them."""
    text = "```\ncode\n```\nprose `alpha` and `beta` here.\n"
    fused = _CODE_SPAN.findall(text)
    clean = _CODE_SPAN.findall(_strip_fences(text))
    assert clean == ["alpha", "beta"], f"the stripper did not restore the pairing: {clean}"
    assert fused != clean, "the fence did not desync anything, so this control proves nothing"


def test_the_citation_parser_ignores_a_fenced_command():
    """A command inside a fence is a runnable example, not a transcription of
    the declaration - and it is also where a shell prompt or a placeholder
    lives."""
    live = _a_declared_command()
    text = f"{SETTINGS_CITATION} is wired.\n\n```\n{live} --stale-flag\n```\n"
    checked, offenders = _check("planted.md", text, _declared_commands())
    assert checked == 0, "a fenced example was graded as a quotation"
    assert not offenders


def test_an_unbalanced_quote_in_prose_is_not_graded_and_no_longer_answers_empty():
    """`shlex` raises on an unbalanced quote. Prose contains those.

    THE FIRST ASSERTION INVERTED, and deliberately. It read
    `assert _tokens('python x.py "unclosed') == []` and so pinned the
    degrade-to-empty as the contract - see `UnparseableCommand` for what that
    empty list certified. The SWEEP-level assertions below are unchanged: a
    phrase in prose that names no declared script is still out of scope, which
    is the survival half this arm has always carried."""
    with pytest.raises(UnparseableCommand):
        _tokens('python x.py "unclosed')
    checked, offenders = _check("planted.md", 'see `python "unclosed` here.', _declared_commands())
    assert checked == 0
    assert not offenders
# ---------------------------------------------------------------------------
# Fail-closed: an unparseable command is UNKNOWN, and UNKNOWN IS NOT CLEAN
#
# `_tokens` answered `[]` when shlex raised. Every caller below it looks FOR
# something in the token list, so zero tokens meant every question came back no
# and the span was waved through - a guard passing on both sides of a real
# defect. These two arms pin the INPUT that causes it, not the shape of a fix.
# ---------------------------------------------------------------------------


def test_tokens_raises_on_an_unparseable_command_rather_than_answering_empty():
    """The control comes FIRST: prove shlex really raises on this input, because
    an arm whose fixture does not trigger the fault is a gate that cannot fail."""
    command = 'python x.py --source "sessionstart'
    with pytest.raises(ValueError) as control:
        shlex.split(command, posix=False)
    assert "quotation" in str(control.value), (
        f"the probe string did not produce the expected shlex failure: {control.value}"
    )

    with pytest.raises(UnparseableCommand) as raised:
        _tokens(command)
    message = str(raised.value)
    assert command in message, f"the failure does not name the command it could not parse: {message}"
    assert str(control.value) in message, (
        f"the raw shlex reason {str(control.value)!r} was swallowed instead of chained: {message}"
    )
    assert isinstance(raised.value.__cause__, ValueError), (
        "the original shlex ValueError was not chained as __cause__, so the cause is lost"
    )


def test_an_unparseable_quotation_of_a_declared_script_is_reported_not_waved_through():
    """The gate-level consequence, and the reason this is not a cosmetic fix.

    A document that transcribes a declared hook command AND drops a quote is
    stale in exactly the way this file exists to catch, and it is the one input
    the old `except ValueError: return []` could not see."""
    script = sorted(_declared_scripts(_declared_commands()))[0]
    command = f'python {script} --source "sessionstart'
    with pytest.raises(ValueError):
        shlex.split(command, posix=False)
    assert command not in _declared_commands(), "the probe accidentally quoted a live declaration exactly"

    checked, offenders = _check("planted.md", f"a hook (`{command}`).", _declared_commands())
    assert checked == 1, f"an unparseable quotation of a declared script was not graded at all: checked={checked}"
    assert offenders, "an unparseable quotation of a declared hook command was waved through as clean"
    assert "planted.md" in offenders[0], f"the report does not name the offending document: {offenders[0]}"
    assert "quotation" in offenders[0], f"the report does not carry the raw shlex reason: {offenders[0]}"
# ---------------------------------------------------------------------------
# APPENDED DELIBERATELY, at the end of the module.
#
# `_tokens` and `_citations` are cited by symbol elsewhere in this file and in
# the docstring at the top. Defining this class and these two helpers above
# `_tokens` would have shifted every line below them. The names resolve out of
# module globals when the functions are CALLED, which is always after import
# completes, so a forward reference costs nothing but one jump for a reader.
# ---------------------------------------------------------------------------


class UnparseableCommand(ValueError):
    """A command string could not be split, so this guard's verdict is UNKNOWN.

    UNKNOWN IS NOT CLEAN. `_tokens` answered an unparseable command with `[]`
    until this class existed, and EVERY caller below it asks whether the token
    list CONTAINS something: `_declared_scripts` looks for a `.py` target,
    `_citations` looks for a declared script and for a `--` flag, and
    `_a_declared_command` looks for a flag. Zero tokens made every one of those
    questions answer no, so an unbalanced quote in a transcription of a hook
    command took the span out of scope entirely and the sweep reported clean -
    a guard passing on both sides of the exact defect it exists to catch.
    Measured this session: `_check` graded 0 citations for a planted document
    quoting a declared hook script with one quote missing.

    Subclasses `ValueError` because it IS one - shlex raises `ValueError` and
    this is re-raised `from` it, so the original stays on the traceback for
    whoever is debugging while the message stays readable for whoever is not.
    """


def _unparseable_reason(command: str, exc: ValueError) -> str:
    """Name the command and the raw shlex reason, without pasting a traceback.

    The raw reason is shlex's own text - measured on this machine 2026-09-11,
    an unbalanced double quote yields exactly `No closing quotation`. It is
    quoted through rather than paraphrased, because a paraphrase of a library
    message goes stale the moment the library rewords it.
    """
    return (
        "UNPARSEABLE, therefore UNKNOWN, therefore FAIL: shlex could not split "
        + repr(command) + " - " + type(exc).__name__ + ", " + str(exc)
        + ". A guard that answers an empty token list for a command it could not "
        + "parse finds nothing in it and reports clean, on both sides of a real "
        + "defect. Fix the quoting in the command, or exclude the span deliberately."
    )


def _scope_tokens(command: str, scripts: frozenset[str]) -> tuple[list[str], str]:
    """`(tokens, reason)` for one code span. A non-empty reason means UNKNOWN.

    `_citations` is the ONE caller that genuinely has to survive a bad span: a
    document is swept span by span, and a single unbalanced backtick-quoted
    phrase must not abort the grading of the other spans in the same tree. So
    the exception is caught HERE, at that one call site, and nowhere else - the
    declaration-side callers (`_declared_scripts`, `_a_declared_command`,
    `test_at_least_one_declared_command_carries_a_long_flag`) let it propagate,
    because an unparseable string in `.claude/settings.json` is a broken
    declaration and must fail loudly rather than be worked around.

    Surviving is not the same as reporting clean. The fallback split is
    FAIL-OPEN ON SCOPE, deliberately in the widening direction: whitespace
    tokens, plus any declared script that merely appears as a SUBSTRING of the
    command, so a span whose quoting hid its script token still reaches the
    scope test. The appended names go at the END of the list, never at index 0,
    which is what `_citations` slices off as the interpreter. The reason then
    makes the citation in-scope on its own, so an unknown span is graded and
    reported instead of skipped.
    """
    try:
        return _tokens(command), ""
    except UnparseableCommand as exc:
        widened = [token.strip("\"'") for token in command.split()]
        widened += [script for script in sorted(scripts) if script in command and script not in widened]
        return widened, str(exc)
def test_the_scope_widening_reaches_a_script_the_whitespace_split_cannot_see():
    """Non-vacuity for the fallback in `_scope_tokens`, which would otherwise be
    an unexercised branch - defensive code that no arm can kill.

    The CONTROL comes first and is the whole arm: it shows the plain whitespace
    split really does miss this script, so the substring pass is what carries
    the span into scope rather than decoration on top of something that already
    worked."""
    scripts = _declared_scripts(_declared_commands())
    script = sorted(scripts)[0]
    # Both halves of this string are measured, on this machine 2026-09-11. A
    # quote that starts MID-WORD is an ordinary character to non-posix shlex, so
    # `foo"` glues the script to a token that `.strip("\"'")` cannot clean up -
    # strip only trims the ENDS. The unclosed single quote on the last token is
    # what makes shlex raise at all; `foo"` alone parses without complaint.
    command = f"""python foo"{script} --source 'sessionstart"""
    with pytest.raises(ValueError):
        shlex.split(command, posix=False)

    plain = [token.strip("\"'") for token in command.split()]
    assert not any(token in scripts for token in plain[1:]), (
        f"the whitespace split already found the script, so this control proves nothing: {plain}"
    )

    widened, reason = _scope_tokens(command, scripts)
    assert reason, "an unparseable command came back with no reason, so it would read as clean"
    assert widened[0] != script, "the widened script landed at index 0, which `_citations` slices off"
    assert any(token in scripts for token in widened[1:]), (
        f"the widening did not reach the declared script: {widened}"
    )

    checked, offenders = _check("planted.md", f"a hook (`{command}`).", _declared_commands())
    assert checked == 1, f"the widened span was not graded: checked={checked}"
    assert offenders, "a span whose script only the widening could see was waved through"
