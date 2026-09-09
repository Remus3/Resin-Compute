"""Every tool the CI gates invoke is pinned, with `==`, in requirements-dev.txt.

WHAT THIS GUARD CLAIMS, and it is deliberately a claim about the DECLARATION.
It reads the TEXT of every workflow file in `.github/workflows/`, ENUMERATED
FROM DISK, derives - OPEN-ENDEDLY - the set of program names their `run:` blocks
put in command position, and asserts that set is exactly the set of names
`requirements-dev.txt` pins, and that every one of those pins is an `==` and not
a floating specifier. That is the whole claim.

THE WORKFLOW SET IS ENUMERATED, NOT NAMED. An earlier revision held `ci.yml` and
`docs-guards.yml` as module constants. `.github/workflows/` holds exactly those
two today, so nothing was being missed today - but a THIRD workflow gate would
have been graded by nothing at all, and the ceiling below did not say so.
Measured on a planted three-workflow tree: a `pip-audit --strict` step in the
third file derived the empty set. `workflow_files()` now lists the directory.
The cost of that is a set that can go EMPTY where a constant could not, so every
arm consuming it welds a census floor into its own assertion.

OPEN-ENDED IS THE LOAD-BEARING WORD, and an earlier revision of this module got
it wrong. That revision looked up a CLOSED dict of exactly ruff, mypy and pytest
and asked which of the three appeared. The derived set could then never contain
a fourth name, so `pinned == invoked` was structurally satisfied and the guard
could not detect the one thing it exists to detect. Measured: adding
`pip-audit --strict` and `pyright core` to ci.yml, neither pinned, left it at
`4 passed`. The derivation below instead classifies EVERY command-position word,
so an unpinned fourth tool lands in `invoked`, is absent from `pinned`, and
reddens the equality half on its own.

THE POLARITY OF THE CLASSIFIER, which is why it can be open-ended at all. The
allow-list below is a list of things that are NOT pinnable tools - shell
keywords, builtins, coreutils, git, and the stdlib `-m` targets this tree uses.
Anything else in command position is treated as a TOOL THAT MUST BE PINNED.
Unknown therefore fails toward the claim rather than away from it. Adding a new
coreutil to a workflow reddens this module until someone adds the word to
`_SHELL_WORDS`; that is the intended cost, and the failure message says so. The
alternative polarity - an allow-list of tool names - is the closed dict that was
just removed, and widening a matcher is this tree's twice-learned wrong answer.

A YAML UNWRAP HAPPENS BEFORE THE SHELL SCAN, and its absence was the THIRD
false green. An inline `run:` value may be a quoted YAML scalar, and quoting is
MANDATORY when a command opens with a character YAML reserves. The scalar's
opening quote used to lead `_SHELL_SYNTAX_LEAD`, so the word classified as shell
syntax and the whole line yielded nothing. Measured before the fix:
`run: "pip-audit --strict"` and `run: 'pip-audit --strict'` each derived the
empty set, so an unpinned tool added that way was invisible and this module
stayed green. `_unquote_yaml_scalar` takes off ONE matched outer pair at the
YAML level, before the shell heuristic runs. THAT IS A PARSE STEP THAT WAS
MISSING AND NOT A WIDER SHELL MATCHER - widening a matcher is this tree's
twice-learned wrong answer, and the shell-quoting rules are unchanged. Malformed
or unbalanced quoting raises `UnclassifiedCommand` naming the file and line.
Block scalar (`run: |`) bodies are literal YAML text, carry no YAML quoting, and
are never unwrapped.

THE CEILING, stated here rather than discovered later. The derivation is a
quote-aware word scanner, not a shell. It credits a tool only when the tool's
BARE NAME stands in COMMAND POSITION in the workflow TEXT. It therefore does
NOT see:

  - an invocation reached through a path (`./bin/pip-audit`, `tools/x.sh`) -
    any word containing `/`, `*` or `?` is read as a path or a glob;
  - an invocation reached through a shell variable (`$LINTER check .`);
  - a tool run from inside a shell script, a composite action or a Makefile the
    workflow merely calls - the text leaves the workflow entirely;
  - `python -m some.dotted.module`, which is read as a module inside a package
    rather than as a distribution invoked by name;
  - a `python foo.py` script invocation, since the pinned thing there would be
    whatever `foo.py` imports, which is not text in this file;
  - A TOOL IN ARGUMENT POSITION. `xargs -0 ruff check` really does run ruff and
    is deliberately left UNCREDITED. This is the one ceiling entry chosen rather
    than inherited, and the reason is that argument position is not decidable
    from the text: without knowing what the outer tool does with its arguments,
    `ruff` there is indistinguishable from a filename, a subcommand or a word of
    prose. Crediting it would mean a per-tool table of which arguments are
    commands, which is the closed dict this module removed. `xargs` stays in
    `_SHELL_WORDS`, the shape is pinned by an arm below so the ceiling is
    enforced and not merely written down, and a tool that must be graded should
    be invoked directly in its own `run:` line.

Every one of those leaves `invoked` EMPTY or SHORT rather than wrong, which is
what the welded floors below catch, and a short derivation that drops one of
ruff, pytest or mypy reddens on `FLOOR`.

WHAT DOES NOT LEAVE IT SHORT, BECAUSE IT RAISES INSTEAD: `${{ ... }}` in command
position, where the program name is not in the file at all; a word that is
neither recognised shell syntax nor a bare program name; `-m` with no module
target; and a malformed inline YAML scalar. Each raises `UnclassifiedCommand`
naming the file and the line. An unparseable shape fails; it is never widened
around. AN EARLIER REVISION OF THIS PARAGRAPH CALLED `${{ ... }}` "the one shape
that could hide a tool name silently". That sentence was MEASURED FALSE - the
quoted scalar hid one silently for three revisions - and it is deleted rather
than softened, because a docstring that overstates its own reach is the defect
these findings keep being about.

WHY NOT AN EQUALITY AGAINST WHAT IS INSTALLED. The obvious guard - assert the
installed ruff/pytest/mypy match the pinned versions - is GREEN ON CI BY
CONSTRUCTION and red on any developer box that has not just reinstalled. CI
pip-installs this very file on `ubuntu-latest` before it runs a single gate, so
the runner is at the pin whatever the pin says; the author's box is measurably
behind it. A guard that can only ever redden locally, and never on the lane
that decides whether a commit ships, is a guard the operator disables, and then
the tree has neither the guard nor the honesty of not having claimed one. The
drift itself is REPORTED, not enforced, by `scripts/qa_companion.py`, which
prints the installed-versus-declared row and never changes an exit code.

WHAT THIS GUARD CANNOT CLAIM - the common-mode risk, stated rather than
implied. It reads `requirements-dev.txt` as the truth about what CI installs,
and it establishes that the workflows install that file only by finding the
`pip install -r requirements-dev.txt` TEXT in a `run:` block. It never observes
a runner, never resolves a dependency, and knows nothing about a transitively
pulled version, a cached wheel, a `pip install --upgrade` elsewhere in the job,
or a constraint applied by the hosted image. If the true premise - "the file
CI installs is this file" - is ever false, every arm below stays green while
saying nothing. Do not read a pass here as a statement about the runner.

NO YAML LIBRARY. PyYAML is installed on the author's box and is NOT in
requirements-dev.txt, which pins ruff, pytest and mypy only. A guard importing
it would pass here and fail on the runner, which is the reverse of useful. The
same rule and the same line-scanner shape are in
`tests/test_ci_history_depth.py`; this module follows it.

CENSUS AND JUDGEMENT IN ONE ASSERT. "Everything the gates invoke is pinned" is
trivially true of a parser that sees no invocations at all - a renamed
workflow, a reindented `run:` block or a scanner that stopped matching would all
make the primary arm pass while measuring nothing. A floor kept in a SEPARATE
arm does not fix that: it leaves a window in which the primary arm is vacuous
and still green, and green is what a reader acts on. So the floor and the
judgement are welded into one assertion in each arm below, and the failure
message says WHICH HALF gave way, because two identical lists under an
equality-shaped assert is what the floor half used to print.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
REQUIREMENTS_DEV = REPO_ROOT / "requirements-dev.txt"

#: The extensions GitHub Actions reads out of `.github/workflows/`. Anything
#: else in that directory is not a workflow and is not graded.
WORKFLOW_SUFFIXES = (".yml", ".yaml")

#: The tools whose absence from the pin file would let a release of that tool
#: redden a commit that changed nothing. This is the anti-vacuity floor, and it
#: is the set requirements-dev.txt's own header prose names. Retiring a tool is
#: a legitimate edit, and it must update this constant IN THE SAME COMMIT - the
#: failure message below says so, because a hardcoded floor that reddens without
#: naming itself is a puzzle rather than a finding.
FLOOR = frozenset({"ruff", "pytest", "mypy"})

_RUN_KEY = re.compile(r"^(?:-\s+)?run:\s*(.*)$")

#: A YAML block scalar header. `run: |` introduces the command lines; it is not
#: itself one.
_BLOCK_HEADER = re.compile(r"^[|>][+-]?$")

#: `name==version` and nothing else. A trailing `; python_version < "3.12"` or a
#: `>=` both fail this deliberately - the pin file's header states `==` is the
#: rule, and an environment marker would make "what CI installs" conditional.
_PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)$")

#: The distribution name at the head of any requirement line, whatever
#: specifier follows. Used to census the file so a FLOATING line is counted and
#: then graded, rather than silently vanishing from the census.
_REQUIREMENT_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")

_PIP_INSTALL_DEV = re.compile(r"pip\s+install\s+(?:[^\s]+\s+)*-r\s+requirements-dev\.txt")

#: A shell variable assignment standing in front of a command, either as a
#: prefix (`FOO=1 python -m pytest`) or as the whole statement (`status=$?`).
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

#: A bare program name: what a distribution is actually called when you type it.
_PROGRAM_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")

#: Shell keywords. Each one is followed by another command in the same word
#: stream, so the scanner steps over it and keeps looking rather than stopping.
_KEYWORDS = frozenset(
    {
        "if",
        "then",
        "elif",
        "else",
        "fi",
        "for",
        "while",
        "until",
        "do",
        "done",
        "case",
        "esac",
        "in",
        "select",
        "function",
        "time",
        "coproc",
        # `! cmd` runs cmd and inverts its status. A reserved word followed by a
        # command, exactly like `time`, so the scanner steps over it and reads
        # the command behind it. It used to lead `_SHELL_SYNTAX_LEAD` instead,
        # which stopped the scan at word zero and hid the tool.
        "!",
    }
)

#: Words that appear in command position in this tree's workflows and are NOT
#: pinnable Python tooling: shell builtins, coreutils, and git. THE LIST IS
#: DELIBERATELY SHORT AND CLOSED. Adding a coreutil to a workflow reddens this
#: module until the word is added here, in the same commit, which is the price
#: of the unknown-means-tool polarity described in the module docstring.
_SHELL_WORDS = frozenset(
    {
        "awk",
        "basename",
        "bash",
        "break",
        "cat",
        "cd",
        "chmod",
        "continue",
        "cp",
        "cut",
        "date",
        "diff",
        "dirname",
        "echo",
        "env",
        "eval",
        "exec",
        "exit",
        "export",
        "false",
        "find",
        "git",
        "grep",
        "head",
        "local",
        "ls",
        "mapfile",
        "mkdir",
        "mv",
        "pip",
        "pip3",
        "printf",
        "pwd",
        "read",
        "readonly",
        "return",
        "rm",
        "sed",
        "seq",
        "set",
        "sh",
        "shift",
        "sleep",
        "sort",
        "source",
        "tail",
        "tee",
        "test",
        "touch",
        "tr",
        "trap",
        "true",
        "umask",
        "uniq",
        "unset",
        "wc",
        "xargs",
    }
)

#: `python -m <target>` where the target ships with the interpreter or with pip
#: itself. These are not pinned in requirements-dev.txt and must not be demanded
#: of it. Same closed-list rule as `_SHELL_WORDS`.
_STDLIB_MODULES = frozenset(
    {
        "compileall",
        "ensurepip",
        "pip",
        "pydoc",
        "site",
        "unittest",
        "venv",
        "zipapp",
    }
)

_PYTHON = frozenset({"python", "python3"})

#: Characters that open shell syntax rather than a program name. A word
#: beginning with one of these is a test bracket, a redirection, a variable
#: expansion, a quoted string, an option, or the `:` no-op - never a tool.
#:
#: THE QUOTES HERE ARE ABOUT SHELL QUOTING, NOT YAML QUOTING, and conflating the
#: two was the third false green. A YAML-quoted `run:` scalar is unwrapped by
#: `_unquote_yaml_scalar` BEFORE this tuple ever sees the command, so a quote
#: reaching here is one the shell would see too.
_SHELL_SYNTAX_LEAD = tuple("$\"'[]:-<>&|;()~{}=+#\\")

#: Splits a command line at every point where a NEW command may begin. `$(` and
#: a backtick open a command substitution; `;`, `|`, `&` and `(`/`)` separate or
#: group commands. Redirections (`>`, `<`) are deliberately absent - what
#: follows them is a filename, not a command.
_COMMAND_BREAK = tuple(";|&()`")


class UnclassifiedCommand(Exception):
    """A `run:` block holds a shape the scanner cannot classify.

    Raised rather than skipped. A word in command position that is neither
    recognised shell syntax nor a bare program name could be hiding a tool - the
    motivating case is `${{ matrix.linter }}`, where the name the runner will
    execute is not in the file at all. This tree's rule is that an unparseable
    shape FAILS and says where, rather than being widened around.
    """


def _unquote_yaml_scalar(value: str, *, source: str, lineno: int) -> str:
    """Return the CONTENT of an inline `run:` value, unwrapping YAML quoting.

    THIS IS A YAML PARSE STEP THAT WAS SIMPLY MISSING, and it is deliberately
    NOT a loosening of the shell heuristic. `run: "pip-audit --strict"` is
    ordinary workflow YAML - quoting is MANDATORY when a command opens with a
    character YAML reserves - and the scalar's CONTENT is the shell line. Before
    this function existed the opening quote led `_SHELL_SYNTAX_LEAD`, the word
    classified as shell syntax, and the whole line yielded no tool at all. That
    was the third false green this module has had, and widening the shell
    matcher is this tree's twice-learned wrong answer to exactly that.

    Only ONE matched outer pair comes off, and only from an INLINE scalar. A
    block scalar (`run: |`) has no YAML quoting in its body at all - those lines
    are literal text - so they are never passed through here.

    Escapes are handled to the extent YAML defines them for a shell command:
    `''` inside a single-quoted scalar, and `\\\\` and `\\"` inside a
    double-quoted one. ANY OTHER backslash escape in a double-quoted scalar
    RAISES rather than being passed through, because YAML's `\\n` and `\\t`
    change the command the runner sees and a scanner that guessed at them would
    silently under-credit. Unterminated quoting, and content after the closing
    quote, raise for the same reason: an unparseable shape must fail and say
    where, never be guessed at.
    """
    if not value or value[0] not in "'\"":
        return value

    quote = value[0]
    body: list[str] = []
    index = 1
    while index < len(value):
        char = value[index]
        if quote == "'":
            if char == "'":
                if index + 1 < len(value) and value[index + 1] == "'":
                    body.append("'")
                    index += 2
                    continue
                index += 1
                break
            body.append(char)
            index += 1
            continue
        if char == "\\":
            following = value[index + 1] if index + 1 < len(value) else ""
            if following in ('"', "\\"):
                body.append(following)
                index += 2
                continue
            raise UnclassifiedCommand(
                f"{source}:{lineno}: a double-quoted YAML scalar carries a"
                f" backslash escape of {following!r}, which this scanner does"
                f" not resolve, in {value!r}. Spell the command in a block"
                " scalar, or teach _unquote_yaml_scalar the escape."
            )
        if char == '"':
            index += 1
            break
        body.append(char)
        index += 1
    else:
        raise UnclassifiedCommand(
            f"{source}:{lineno}: an inline `run:` value opens with {quote!r} and"
            f" never closes it, so it is not a YAML scalar this scanner can"
            f" read: {value!r}. An unparseable shape fails rather than being"
            " guessed at."
        )

    if index != len(value):
        raise UnclassifiedCommand(
            f"{source}:{lineno}: an inline `run:` value has content after the"
            f" closing {quote!r}, so it is not a single quoted YAML scalar:"
            f" {value!r}. An unparseable shape fails rather than being guessed"
            " at."
        )
    return "".join(body)


def _strip_shell_comment(line: str) -> str:
    """Drop a trailing `#` comment, honouring quotes and word boundaries.

    A `#` opens a comment only when it is unquoted AND begins a word - at the
    start of the line or after whitespace. That is the POSIX rule, and it is
    what keeps `"${#app[@]}"` intact; docs-guards.yml uses that expansion four
    times, and a naive `split('#')` would truncate those lines mid-command.

    THE CASE THIS DOES NOT DECIDE PERFECTLY: a `#` inside a quoted string is
    treated as literal text, which is correct for the shell, and quoting state
    is tracked with a simple single/double-quote toggle plus backslash escape.
    A here-document body, or a quote nested through a command substitution, can
    desynchronise that toggle. No workflow line in this tree does either; if one
    ever does, the resulting word is far more likely to be unclassifiable - and
    so raise - than to be silently mistaken for a tool.
    """
    out: list[str] = []
    quote: str | None = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            out.append(char)
            escaped = False
            continue
        if quote is None and char == "\\":
            out.append(char)
            escaped = True
            continue
        if quote is not None:
            out.append(char)
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            out.append(char)
            quote = char
            continue
        if char == "#" and (index == 0 or line[index - 1].isspace()):
            break
        out.append(char)
    return "".join(out).rstrip()


def _split_segments(command: str) -> list[str]:
    """Cut a command line wherever a new command may begin, honouring quotes."""
    segments: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for char in command:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if quote is None and char == "\\":
            current.append(char)
            escaped = True
            continue
        if quote is not None:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            current.append(char)
            quote = char
            continue
        if char in _COMMAND_BREAK:
            segments.append("".join(current))
            current = []
            continue
        current.append(char)
    segments.append("".join(current))
    return segments


def _split_words(segment: str) -> list[str]:
    """Whitespace-split a segment without splitting inside quotes."""
    words: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for char in segment:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if quote is None and char == "\\":
            current.append(char)
            escaped = True
            continue
        if quote is not None:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            current.append(char)
            quote = char
            continue
        if char.isspace():
            if current:
                words.append("".join(current))
                current = []
            continue
        current.append(char)
    if current:
        words.append("".join(current))
    return words


def _is_path_or_glob(word: str) -> bool:
    """A word naming a file rather than a program on PATH.

    Case-statement patterns (`tests/*)`), `find` arguments and quoted paths all
    land here. So does a genuine `./bin/pip-audit`, which is the ceiling the
    module docstring records: an invocation by path is not credited.
    """
    return any(char in word for char in "/*?")


def _classify(words: list[str], *, source: str, line: str) -> str | None:
    """The tool name this word stream invokes, or None if it invokes no tool.

    Raises `UnclassifiedCommand` for a shape that is neither shell syntax nor a
    bare program name, because such a shape may be hiding a tool name.
    """
    index = 0
    while index < len(words):
        word = words[index]
        if _ASSIGNMENT.match(word) or word in _KEYWORDS:
            index += 1
            continue
        break
    else:
        return None
    word = words[index]
    if word.startswith("${{"):
        raise UnclassifiedCommand(
            f"{source}: a GitHub expression stands in command position, so the"
            f" program name is not in the file and cannot be graded: {line!r}."
            " Spell the tool literally, or teach this scanner the shape."
        )
    if word.startswith(_SHELL_SYNTAX_LEAD) or _is_path_or_glob(word):
        return None
    if not _PROGRAM_NAME.match(word):
        raise UnclassifiedCommand(
            f"{source}: {word!r} stands in command position and is neither"
            f" recognised shell syntax nor a bare program name, in {line!r}."
            " This scanner refuses to guess; classify the shape explicitly in"
            " tests/test_dev_pin_declaration.py."
        )
    if word in _PYTHON:
        rest = words[index + 1 :]
        if "-m" not in rest:
            return None
        target_index = rest.index("-m") + 1
        if target_index >= len(rest):
            raise UnclassifiedCommand(
                f"{source}: `-m` with no module target in {line!r}."
            )
        target = rest[target_index]
        if "." in target or target in _STDLIB_MODULES or _is_path_or_glob(target):
            return None
        if not _PROGRAM_NAME.match(target):
            raise UnclassifiedCommand(
                f"{source}: {target!r} is not a bare module name in {line!r}."
            )
        return target
    if word in _SHELL_WORDS:
        return None
    return word


def iter_command_lines(text: str, *, source: str = "<planted>") -> list[str]:
    """Every line of shell the workflow hands a runner, and nothing else.

    A `run:` key opens a command context. When its value is inline the value IS
    the command - after `_unquote_yaml_scalar` takes off any YAML quoting, which
    is a parse step and not a shell one. When the value is a block scalar
    (`|`, `>`) the commands are the lines indented further than the `run:` key
    itself, up to the first line that is not; those lines are LITERAL YAML text
    and carry no YAML quoting, so they are never unwrapped. Blank lines are
    dropped, and every line has its trailing `#` comment stripped before it is
    returned - an earlier revision stripped only WHOLE-LINE comments, so
    `run: echo lint step deleted  # ruff check .` left the guard green while
    ruff was no longer being run at all.

    Everything outside a `run:` block is invisible here, which is the point: a
    step spelled `- name: mypy` is a LABEL and not an invocation, and a scanner
    that credited it would report a gate the runner never executes. A control
    below plants exactly that label, plus a commented-out invocation.
    """
    commands: list[str] = []
    run_indent: int | None = None
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        if run_indent is not None:
            if not stripped:
                continue
            if indent > run_indent:
                body = _strip_shell_comment(stripped)
                if body:
                    commands.append(body)
                continue
            run_indent = None
        if stripped.startswith("#"):
            continue
        match = _RUN_KEY.match(stripped)
        if match is None:
            continue
        run_indent = raw.index("run:")
        body = _strip_shell_comment(match.group(1).strip())
        if body and not _BLOCK_HEADER.match(body):
            unwrapped = _unquote_yaml_scalar(body, source=source, lineno=lineno)
            if unwrapped:
                commands.append(unwrapped)
    return commands


def invoked_tools(text: str, *, source: str = "<planted>") -> set[str]:
    """Every program name the run blocks put in command position, minus shell.

    Open-ended by construction: the classifier knows what is NOT a tool and
    returns everything else, so a tool nobody has heard of is still counted.
    """
    found: set[str] = set()
    for command in iter_command_lines(text, source=source):
        for segment in _split_segments(command):
            words = _split_words(segment)
            if not words:
                continue
            tool = _classify(words, source=source, line=command)
            if tool is not None:
                found.add(tool.lower())
    return found


def workflow_files(directory: Path = WORKFLOWS_DIR) -> list[Path]:
    """Every workflow GitHub Actions would run, ENUMERATED FROM DISK.

    Two filenames used to be module constants. `.github/workflows/` holds
    exactly those two today, so nothing was being missed today - but a THIRD
    workflow gate would have been entirely ungraded, and the stated ceiling
    below never said so. Measured on a planted three-workflow tree before this
    change: a `pip-audit --strict` step in the third file derived nothing.

    A hardcoded list cannot go stale silently now; an EMPTY list can, so every
    arm that consumes this welds a floor into its own assertion rather than
    keeping one in a separate arm.
    """
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix in WORKFLOW_SUFFIXES
    )


def gate_invoked_tools() -> set[str]:
    """The union over every workflow file, which together are the CI gate."""
    found: set[str] = set()
    for path in workflow_files():
        found |= invoked_tools(path.read_text(encoding="utf-8"), source=path.name)
    return found


def requirement_lines(text: str) -> list[str]:
    """Every non-blank, non-comment line of a requirements file."""
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def pinned_names(text: str) -> set[str]:
    """The distribution name of every requirement line, pinned or not.

    Deliberately NOT restricted to `==` lines. If a pin were loosened to `>=`
    the name must still appear in this census, so that the equality arm stays
    green and the FLOATING arm below is the one that reddens - one defect, one
    red test, naming the actual fault.
    """
    names = set()
    for line in requirement_lines(text):
        match = _REQUIREMENT_NAME.match(line)
        if match:
            names.add(match.group(1).lower())
    return names


def floating_requirements(text: str) -> list[str]:
    """Every requirement line that is not an exact `name==version` pin."""
    return [line for line in requirement_lines(text) if not _PIN.match(line)]


def _declaration_report(
    invoked: set[str], pinned: set[str], workflows: list[Path]
) -> str:
    """Say WHICH half of the welded assertion gave way, and what to do.

    The equality half and the floor half print two different things. Under the
    old single-sentence message a floor failure printed `gates invoke [a, b];
    requirements-dev.txt pins [a, b]` - two IDENTICAL lists under an
    equality-shaped assert, with no mention of the floor and no hint that a
    deliberate retirement has to update a constant in this file.
    """
    parts: list[str] = []
    if not workflows:
        parts.append(
            "NO WORKFLOWS ENUMERATED."
            f" {WORKFLOWS_DIR} holds no {' or '.join(WORKFLOW_SUFFIXES)} file,"
            " so the derivation graded nothing at all and every other half of"
            " this assertion is a statement about no input. Either the"
            " directory moved or the gate was deleted."
        )
    if invoked != pinned:
        parts.append(
            "DECLARATION MISMATCH."
            f" Invoked by a gate but not pinned: {sorted(invoked - pinned)}."
            f" Pinned but invoked by no gate: {sorted(pinned - invoked)}."
            " A name in the first list is either a tool needing an `==` pin in"
            " requirements-dev.txt or an ordinary shell word needing to join"
            " _SHELL_WORDS in this file - the scanner treats unknown as tool"
            " deliberately."
        )
    if not invoked >= FLOOR:
        parts.append(
            "ANTI-VACUITY FLOOR UNMET."
            f" FLOOR requires {sorted(FLOOR)} and the derivation found"
            f" {sorted(invoked)}, missing {sorted(FLOOR - invoked)}."
            " Either the scanner stopped seeing the workflows - a rename, a"
            " reindent, an invocation moved into a shell script - or a tool was"
            " retired on purpose, in which case update FLOOR in"
            " tests/test_dev_pin_declaration.py in the SAME commit."
        )
    return " ".join(parts)


def test_every_tool_the_gates_invoke_is_pinned_in_requirements_dev():
    """The declaration matches the gate, and the gate is not empty.

    ONE ASSERT, THREE HALVES, and the reason is in the module docstring: the
    equality alone is satisfied by two empty sets, so a scanner that stopped
    matching - or a workflow directory that emptied or moved - would report a
    perfect declaration about nothing. Both floors are welded in so an empty
    derivation FAILS rather than passing trivially, and the report says which
    one gave way.
    """
    workflows = workflow_files()
    invoked = gate_invoked_tools()
    pinned = pinned_names(REQUIREMENTS_DEV.read_text(encoding="utf-8"))
    assert pinned == invoked and invoked >= FLOOR and workflows, _declaration_report(
        invoked, pinned, workflows
    )


def test_no_pin_floats():
    """Every requirement is an exact `==`, and there are requirements to grade.

    Same welding. "No line floats" is trivially true of an empty file, and an
    accidentally emptied requirements-dev.txt is exactly the edit that would
    make the arm above meaningless too.
    """
    text = REQUIREMENTS_DEV.read_text(encoding="utf-8")
    floating = floating_requirements(text)
    assert not floating and len(requirement_lines(text)) >= len(FLOOR), (
        f"floating: {floating}; total requirement lines:"
        f" {len(requirement_lines(text))}"
    )


def test_every_workflow_installs_the_pin_file_it_is_being_graded_against():
    """The premise of every arm above, asserted as far as text can assert it.

    If CI stopped installing requirements-dev.txt the pins would be decoration
    and this module would be grading a file nothing reads. This arm is the
    weakest link and the docstring says so: it finds the `pip install -r`
    SPELLING in a run block. It cannot see a cached wheel, a later upgrade, or
    a constraint the hosted image applies. It does now see a COMMENTED-OUT
    spelling for what it is, because `iter_command_lines` strips trailing
    comments.

    The census is welded in for the same reason as above: "no workflow is
    missing the install" is trivially true of no workflows, and this arm used to
    iterate two hardcoded filenames that could not have gone empty.
    """
    workflows = workflow_files()
    missing = [
        path.name
        for path in workflows
        if not any(
            _PIP_INSTALL_DEV.search(command)
            for command in iter_command_lines(
                path.read_text(encoding="utf-8"), source=path.name
            )
        )
    ]
    assert not missing and workflows, (
        f"workflows that never install requirements-dev.txt: {missing};"
        f" workflows enumerated from {WORKFLOWS_DIR}:"
        f" {[path.name for path in workflows]}"
    )


def test_the_command_scanner_reads_invocations_and_not_labels_or_prose():
    """The non-vacuity control: the detector fires, and only on real commands.

    Every negative below is a shape actually present in this tree's workflows -
    a `- name: mypy` step label, a `pytest.ini` path filter, prose naming all
    three tools, and a commented-out command. A scanner that credited any of
    them would report a gate the runner does not run.
    """
    planted = "\n".join(
        [
            "jobs:",
            "  build:",
            "    steps:",
            "      # ruff check . is what this step used to do",
            "      - name: mypy",
            "        run: echo hello",
            "      - name: suites",
            "        run: |",
            "          # mypy",
            "          python -m pytest -rs tests",
            "    paths:",
            "      - 'pytest.ini'",
            "      - 'mypy.ini'",
        ]
    )
    assert invoked_tools(planted) == {"pytest"}, iter_command_lines(planted)

    real = planted.replace("run: echo hello", "run: mypy").replace(
        "- 'mypy.ini'", "- 'mypy.ini'\n      - 'ruff.toml'"
    )
    assert invoked_tools(real) == {"pytest", "mypy"}, iter_command_lines(real)

    both = real.replace("python -m pytest -rs tests", "ruff check .\n          mypy")
    assert invoked_tools(both) == {"ruff", "mypy"}, iter_command_lines(both)


def test_the_scanner_credits_a_tool_it_has_never_heard_of():
    """The open-endedness arm, and the one the closed-dict revision failed.

    If this arm ever needs a name added to a list somewhere before it passes,
    the derivation has gone closed again and the primary assertion above has
    stopped being able to detect the thing it exists for.
    """
    planted = "\n".join(
        [
            "    steps:",
            "      - name: audit",
            "        run: pip-audit --strict",
            "      - name: second opinion",
            "        run: |",
            "          pyright core",
            "          FOO=1 python -m nox --session lint",
            "      - name: pinned installs are not invocations",
            "        run: pip install -r requirements-dev.txt",
        ]
    )
    assert invoked_tools(planted) == {"pip-audit", "pyright", "nox"}


def test_a_trailing_comment_cannot_hide_a_deleted_gate():
    """The regression arm for the second false green, measured on this tree.

    `run: echo lint step deleted  # ruff check .` left the old scanner reporting
    ruff as invoked while the runner ran `echo`. The first assertion is the bug;
    the second is its non-vacuity twin, proving the stripper takes the comment
    and not the command.
    """
    hidden = "        run: echo lint step deleted  # ruff check .\n"
    assert invoked_tools(hidden) == set(), iter_command_lines(hidden)

    live = "        run: ruff check .  # this comment is not the command\n"
    assert invoked_tools(live) == {"ruff"}, iter_command_lines(live)


def test_a_hash_inside_quotes_is_not_a_comment():
    """`${#app[@]}` survives the stripper, which docs-guards.yml depends on.

    Four lines of that workflow expand an array length inside a double-quoted
    string. A stripper that cut at the first `#` would truncate them, dropping
    real command text and quietly shrinking the census.
    """
    line = '        run: echo "app has ${#app[@]} entries"\n'
    assert iter_command_lines(line) == ['echo "app has ${#app[@]} entries"']
    assert invoked_tools(line) == set()


def test_an_unclassifiable_command_shape_fails_rather_than_being_ignored():
    """The stated ceiling is enforced, not merely documented.

    A `${{ ... }}` expression in command position means the program the runner
    executes is not spelled in the file. The scanner refuses it by name instead
    of skipping it, and the control arm proves the refusal is not firing on
    ordinary text.
    """
    hidden = "        run: ${{ matrix.linter }} check .\n"
    with pytest.raises(UnclassifiedCommand) as excinfo:
        invoked_tools(hidden, source="ci.yml")
    assert "ci.yml" in str(excinfo.value)
    assert "matrix.linter" in str(excinfo.value)

    assert invoked_tools("        run: ruff check .\n") == {"ruff"}


def test_a_quoted_yaml_scalar_cannot_hide_a_tool():
    """The THIRD false green, and the one that falsified this module's prose.

    An inline `run:` value may be a quoted YAML scalar, and quoting is MANDATORY
    when the command opens with a character YAML reserves. Measured before the
    fix: all three spellings below yielded `set()` except the bare one, because
    the scalar's opening quote is in `_SHELL_SYNTAX_LEAD` and so the whole line
    classified as no-tool. An unpinned tool added that way was invisible.

    The bare arm is the paired control: it passed before the fix and must keep
    passing, so this is a YAML unwrap being added and not a shell heuristic
    being loosened.
    """
    double = '        run: "pip-audit --strict"\n'
    assert invoked_tools(double) == {"pip-audit"}, iter_command_lines(double)

    single = "        run: 'pip-audit --strict'\n"
    assert invoked_tools(single) == {"pip-audit"}, iter_command_lines(single)

    bare = "        run: pip-audit --strict\n"
    assert invoked_tools(bare) == {"pip-audit"}, iter_command_lines(bare)


def test_a_quoted_scalar_is_unwrapped_at_the_yaml_level_and_not_at_the_shell_one():
    """The unwrap is one matched OUTER pair, and shell quoting is untouched.

    `run: "echo \\"hi\\""` is a YAML double-quoted scalar whose CONTENT is the
    shell line `echo "hi"`, and the inner quotes must survive into the shell
    scan. The second arm is the shape docs-guards.yml actually contains - a
    quote appearing INSIDE a bare scalar is not an outer pair and is left alone.
    """
    escaped = '        run: "echo \\"hi\\""\n'
    assert iter_command_lines(escaped) == ['echo "hi"']
    assert invoked_tools(escaped) == set()

    inner = '        run: echo "app has ${#app[@]} entries"\n'
    assert iter_command_lines(inner) == ['echo "app has ${#app[@]} entries"']
    assert invoked_tools(inner) == set()

    doubled = "        run: 'it''s fine'\n"
    assert iter_command_lines(doubled) == ["it's fine"]


def test_a_malformed_quoted_scalar_raises_rather_than_being_guessed():
    """An unparseable shape FAILS, and says which file and which line.

    None of these is a legal YAML flow scalar. Guessing at them is how the two
    previous false greens happened, so the scanner refuses by name instead.
    """
    for value in ['"pip-audit --strict', "'pip-audit --strict", '"a" && "b"']:
        text = "        run: " + value + "\n"
        with pytest.raises(UnclassifiedCommand) as excinfo:
            invoked_tools(text, source="ci.yml")
        assert "ci.yml" in str(excinfo.value), value
        assert value in str(excinfo.value), value

    assert invoked_tools('        run: "ruff check ."\n') == {"ruff"}


def test_a_shell_negation_prefix_does_not_hide_the_tool():
    """`! ruff check .` runs ruff and inverts its status. The tool is ruff.

    Measured before the fix: this yielded `set()`, because `!` led
    `_SHELL_SYNTAX_LEAD` and stopped the scan at word zero. `!` is a POSIX
    reserved word followed by a command, exactly like the `time` already in
    `_KEYWORDS`, so it belongs there and the scanner steps over it.

    `!ruff` with no space is not shell negation and is not a program name
    either, so it raises rather than being guessed at.
    """
    assert invoked_tools("        run: ! ruff check .\n") == {"ruff"}
    assert invoked_tools("        run: ! pip-audit --strict\n") == {"pip-audit"}

    with pytest.raises(UnclassifiedCommand):
        invoked_tools("        run: !ruff check .\n", source="ci.yml")


def test_a_tool_invoked_as_an_argument_to_another_tool_is_not_credited():
    """A CEILING PIN, not a regression arm - this passed before the fix too.

    `xargs -0 ruff check` really does run ruff, and this scanner does not credit
    it. Command position is the only position it reads, and a tool name standing
    in ARGUMENT position cannot be told from a filename, a subcommand or a word
    of prose without knowing what the outer tool does with its arguments. The
    module docstring names this shape; the arm is here so the ceiling is
    enforced rather than merely written down, and so a future widening that
    quietly starts crediting arguments has to come past a red test and restate
    the claim.
    """
    assert invoked_tools("        run: xargs -0 ruff check\n") == set()
    assert invoked_tools("        run: ruff check .\n") == {"ruff"}


def test_the_graded_workflow_set_is_read_from_disk_and_is_not_empty():
    """FINDING TWO: the set used to be two module constants.

    `.github/workflows/` holds exactly those two names today, so nothing was
    being missed - but a THIRD workflow gate would have been ungraded, and that
    was not in the stated ceiling. Measured on a planted three-workflow tree
    before this change: the third file's `pip-audit --strict` derived nothing.

    The floor is welded into the same assertion, not kept in a sibling arm: an
    empty enumeration must FAIL rather than agreeing with an empty disk.
    """
    graded = sorted(path.name for path in workflow_files())
    on_disk = sorted(
        entry.name
        for entry in WORKFLOWS_DIR.iterdir()
        if entry.is_file() and entry.name.rsplit(".", 1)[-1] in ("yml", "yaml")
    )
    assert graded == on_disk and graded, (
        f"graded {graded}; on disk under {WORKFLOWS_DIR}: {on_disk}"
    )


def test_the_enumeration_picks_up_a_third_workflow_and_skips_a_non_workflow(tmp_path):
    """The enumerator itself, on a tree this test controls.

    The arm above compares two expressions over the SAME two real files, which
    cannot distinguish a correct enumerator from a lucky one. This one plants a
    third workflow, a `.yaml` spelling and a file that is not a workflow at all,
    so the behaviour is pinned rather than the coincidence.
    """
    for name in ("ci.yml", "docs-guards.yml", "tier3.yml", "release.yaml"):
        (tmp_path / name).write_bytes(b"jobs: {}\n")
    (tmp_path / "README.md").write_bytes(b"not a workflow\n")
    (tmp_path / "fragments").mkdir()

    assert [path.name for path in workflow_files(tmp_path)] == [
        "ci.yml",
        "docs-guards.yml",
        "release.yaml",
        "tier3.yml",
    ]
    assert workflow_files(tmp_path / "nonexistent") == []


def test_a_third_workflow_invoking_an_unpinned_tool_would_be_caught(tmp_path):
    """The finding, as a behavioural arm rather than a shape one.

    This is what the hardcoded pair could not do. The planted third workflow
    invokes a tool nothing pins, and the derivation over the enumerated
    directory has to surface it.
    """
    (tmp_path / "ci.yml").write_bytes(b"jobs:\n  a:\n    steps:\n      - run: ruff check .\n")
    (tmp_path / "tier3.yml").write_bytes(
        b"jobs:\n  c:\n    steps:\n      - run: pip-audit --strict\n"
    )

    found: set[str] = set()
    for path in workflow_files(tmp_path):
        found |= invoked_tools(path.read_text(encoding="utf-8"), source=path.name)
    assert found == {"ruff", "pip-audit"}
