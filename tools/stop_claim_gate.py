#!/usr/bin/env python3
"""Session CLAIM gate - checks the REPORT against the transcript's own evidence.

This tree already gates the ARTIFACT: `tools/caveman_default.py` at SessionStart,
`tools/precommit_gate.py` from `.githooks/pre-commit` and `.githooks/commit-msg`,
and the push guards. Nothing gated the REPORT. Three prose-falsity findings in
recent sessions were caught by a human reading the chat, not by a check.

WHAT IT DOES
------------
Reads a session transcript (JSONL, one JSON object per line), builds an EVIDENCE
model from tool output, extracts CLAIMS from assistant text, and reports where a
claim outruns the evidence.

PROVENANCE DECIDES CREDITING. SHAPE ONLY DECIDES PARSING.
--------------------------------------------------------
This is the load-bearing decision in the file, and it replaces an earlier design
that decided crediting on the LEXICAL SHAPE of a line alone.

Shape cannot tell a measurement from an aspiration. Two independent adversarial
passes over real transcripts refuted the earlier design with lines it credited
that no run had produced - a `target:` prefix, a `stale:` prefix, `grep` output
carrying a file and line number, and a comment marker separated from the counts
by a tab. Every patch to the lexical bar traded one false positive for another
laundering hole, because the bar and the laundering share a single dimension.

So a summary line is credited ONLY when the tool result carrying it came from a
command `classify_command()` calls a TEST RUNNER or a CI READER. `cat`, `grep`,
`git log`, `head`, `find`, and every non-shell tool - `Read`, `Grep`, `Edit`,
`Agent` - are none of those, so a stale or aspirational count sitting in a
tracked file is not evidence BY CONSTRUCTION. There is no lexical bar left for
it to slip past, because it never reaches the parser.

WHAT COUNTS AS A RUNNER, AND WHY THE HEAD OF EACH SEGMENT IS WHAT IS READ
------------------------------------------------------------------------
`classify_command()` splits a command on `&&`, `||`, `;`, `|` and newlines, and
asks of each segment: after skipping launchers (`&`, `sudo`, `timeout`, ...),
`VAR=value` assignments, numeric arguments and option flags, is the head token a
test runner or a Python interpreter? ANY runner segment makes the whole command
a runner, which is what lets `cd "..." && python -m pytest tests` be credited -
the shape this project actually writes.

A Python INTERPRETER counts, not only a literal `pytest`. That is a deliberate
widening, and it is the one place this file trades a little safety for a lot of
recall: `python "<scratchpad>/mutate.py"` and `python - <<'PY'` are how mutation
harnesses in this fleet run pytest, and their output lines are genuine runs.
Execution is the line drawn, and every reader named above stays on the far side
of it. The residual is stated under LIMITS below rather than hidden.

A head token that is a shell VARIABLE (`& $py -m pytest`) cannot be resolved, so
for that case alone the segment is searched for a `pytest` token. A head that IS
a resolvable name and is not a runner ends the question for that segment, which
is what stops `grep pytest docs/` from being read as a run.

ONE-HOP REDIRECT CHAINING
-------------------------
Provenance alone refused this project's own standing convention. Because an exit
code read through a pipe is the pipe's, sessions here write

    python -m pytest tests > out.txt 2>&1
    echo "exit=$?"
    tail -2 out.txt

The suite really ran and its summary really is in the transcript, but the
command that PRINTED the summary is `tail`, which is not a runner. Measured over
the 313-transcript corpus: 506 of the 545 false positives the previous build
shipped with were this ONE shape.

So a RUNNER's shell redirection target is recorded as SEEDED, and a later
command that would otherwise be `other` and whose text carries a seeded path has
its output credited to the list that seeded it. Six bars keep that from
re-opening the laundering surface provenance closed, and each has its own test:

  1. THE SEEDING COMMAND MUST ITSELF BE A RUNNER. `echo "930 passed ... in
     17.50s" > out.txt` then `cat out.txt` credits nothing, and so does any
     redirection by a command classified `other`. `cp LEDGER.md out.txt` is not
     a shell redirection at all, so it seeds nothing either.
  2. A NON-RUNNER WRITE TO A SEEDED PATH REVOKES IT, permanently and for the
     whole transcript, in BOTH directions of order. After `pytest > f` then
     `echo "999 passed ... in 1.0s" >> f`, nothing read out of `f` is credited -
     not even the genuine line, because once they share a file they cannot be
     told apart. Revoking is the safe direction.
  3. NO SECOND HOP. `cat a.txt > b.txt` is a non-runner write to `b.txt`, so
     bar 2 revokes it and a copy never inherits the seed.
  4. ORDER MATTERS. Seeds are recorded as the transcript is walked forward, so a
     read of a path BEFORE any runner seeded it credits nothing. Evidence cannot
     flow backwards.
  5. THE SEED IS PER PATH, NOT PER BASENAME. A read is matched against whole
     TOKENS of the command, never against a substring, so `out.txt.bak` does not
     harvest a seed recorded for `out.txt`.
  6. A CI-CLASSIFIED COMMAND'S REDIRECTION SEEDS THE CI LIST. The two lists stay
     separate through the hop, and a command that reads both a CI-seeded and a
     runner-seeded path is credited CI - the same conservative direction
     `classify_command` already takes.

WHAT THE HOP CANNOT DO, STATED RATHER THAN IMPLIED
--------------------------------------------------
  - A BARE RELATIVE PATH CANNOT BE DISAMBIGUATED BY DIRECTORY. `cd a && pytest >
    out.txt` and `cd b && tail out.txt` both normalise to `out.txt` and the hop
    credits the second from the first. Nothing in the command text distinguishes
    them, and this file does not pretend otherwise. Two ABSOLUTE paths that
    differ only in directory ARE distinguished, which is what bar 5 pins.
  - PATHS ARE COMPARED CASE-INSENSITIVELY, because this fleet runs on Windows
    where two casings name one file. On a case-sensitive filesystem that
    over-matches: safe for revocation, a small over-credit for reads.
  - ONLY SHELL REDIRECTION AND `tee` ARE READ AS WRITES. `--junitxml`, `tee-object`,
    `Out-File` and a program's own `-o` flag are not, so they neither seed nor
    revoke.

THE TWO EVIDENCE LISTS ARE NEVER MERGED
---------------------------------------
`Evidence` keeps `local_runs` and `ci_fetches` apart. Folding them makes "this
session ran tests" true for a session that only fetched a CI log and ran
nothing.

The one place the two are unioned is `credited_pass_counts()`, used only by
`count_mismatch`. That union is sound for that question alone: a number really is
supported whether a local run or a CI log produced it. It is NOT sound for "did
this session run anything", which is why `ran_tests_locally()` and `fetched_ci()`
are separate predicates and neither consults the other.

TOOL NAME CANNOT SEPARATE CI FROM LOCAL
---------------------------------------
Every CI log in this fleet's transcripts arrives through the `Bash` tool as
`gh run view <id> --log`, alongside thousands of other Bash calls. Tool name
alone would credit a CI fetch as a local run. The COMMAND TEXT is the
discriminator, and a compound command that touches CI at all is classified CI -
under-crediting a local run is the safe direction, laundering a CI number as
local is not.

WHAT THE LEXICAL GRAMMAR STILL REFUSES, AND WHAT IT NO LONGER DOES
------------------------------------------------------------------
With provenance doing the crediting, the grammar's only job is to recognise a
pytest terminal summary inside a line that a runner printed. It was loosened
accordingly, because the strictness it used to carry was refusing genuine runs:

  - A LABEL PREFIX IS FINE, whatever separator it uses. Because an exit code
    read through a pipe is the pipe's, sessions here write `cmd > file` and
    report `full-suite run 1 EXIT=0  841 passed, 1 skipped in 14.64s`.
  - A TRAILING SUFFIX AFTER THE DURATION IS FINE. This project's own harnesses
    print `28 passed in 0.07s           exit=0` and
    `MUT a_neuter_heal: exit=1 tail=3 failed, 8 passed in 0.63s`.
  - THE REQUIRED `in <float>s` DURATION IS KEPT. A tally with no duration is not
    a pytest terminal summary, which is what keeps qa_companion's
    `16 passed, 0 failed, 2 skipped` from being read as a pytest count.
  - EVERY COUNT WORD MUST BE ONE PYTEST EMITS. An unknown word rejects that
    match; the scan then continues along the line rather than giving up on it,
    so one unparseable tally cannot hide a real summary printed after it.
  - `subtests` IS A COUNT WORD, normalised from pytest-subtests' two-word
    `4575 subtests passed` to the one-word form the grammar takes. Its absence
    had been refusing a real `19547 passed ... in 177.97s` run outright.

THERE IS NO COMMENT-MARKER CHECK, AND ITS DELETION WAS MEASURED
---------------------------------------------------------------
An earlier version refused any line containing `#`, to stop a CI log's echo of a
workflow FILE from laundering a stale count out of a comment. It was removed and
the removal measured rather than argued - see MEASURED below. Under provenance
it decided no case that provenance had not already decided, and a rule whose
mutant nothing catches is dead code.

THE GATE NEVER QUOTES WHAT IT CAUGHT
------------------------------------
A gate that echoes the transcript republishes it. Findings carry a name, a record
index and a detail built only from numbers and fixed English. No transcript text
reaches a finding.

TWO FINDINGS, NOT THREE
-----------------------
A third name, `tests_pass_without_run`, was deleted with its check. It armed only
when every evidence list was empty, which made the supported-count set empty,
which made every count claim a `count_mismatch` - so its offender set is a
strict subset of another check's by construction, not by accident.

Re-measured against THIS evidence model rather than carried forward from a
brief: over the 313-transcript corpus it would arm on 3172 claims, emit 3
findings, and 0 of those 3 name a record `count_mismatch` had not already
flagged. A name in `FINDING_NAMES` that cannot say anything of its own is the
defect this gate exists to catch.

MEASURED 2026-09-07, ON 313 REAL TRANSCRIPTS
--------------------------------------------
Every number below was produced by running THIS build over the transcript corpus
on this machine - 313 files, 254497 records. This session's own transcript is
excluded: it was still being appended to while it was being read, and it carries
this rebuild's adversarial fixtures as data, so it is not a valid subject.

THE CORPUS IS LIVE. Other sessions append to their transcripts while it is being
read, so re-running moves the absolute counts by a few records - 5572 against
5574 across two runs an hour apart. The ratios below were stable across both.

  - CREDITED: 5574 local runs, 99 CI summary lines, 2058 CI commands.
  - EXAMINED: 3172 count claims, 646 CI-green claims.
  - FLAGGED: 801 `count_mismatch`, 3 `ci_green_without_fetch`.
  - THE COMMENT-MARKER CHECK, reinstated as an in-memory mutant, moved credited
    local runs from 5574 to 5573 and changed 0 findings in either check, in 0
    transcripts. One line in 5574 is the whole of what it decided. It was also
    trivially bypassed: `normalise_log_line` keeps only what follows the last
    tab, so `# stale historical:<TAB>930 passed ...` reached the old bar with
    its marker already stripped. That is why it is deleted rather than
    documented.
  - `red` AS A NEGATION WORD was removed on measurement, not on taste. It is the
    only negation word present in 8 CI-green clauses across the corpus, and 7 of
    those 8 are genuine green claims narrating a recovery - "CI on main is
    green, so nothing is inherited-red". Suppressing them is the failure mode
    the negation guard was added to avoid, pointed the other way.
  - ADDING `not`, `never` AND `no` to the negation set was TRIED AND REJECTED.
    It would cut examined CI-green claims from 646 to 567 and findings from 3 to
    1, but of the 79 clauses it suppresses the large majority are genuine claims
    carrying a virtuous qualifier - "CI is green, read from the run, not
    predicted". A guard that blinds the gate on the most carefully reported
    sessions is worse than the two false positives it removes.
  - `gh` INVOKED BY ABSOLUTE PATH was missed by the CI patterns until this pass.
    Fixing it moved `ci_green_without_fetch` from 43 findings to 3 over the same
    corpus, so 40 of the 43 were sessions that HAD read CI.

THE FALSE-POSITIVE RATE THIS BUILD SHIPS WITH, AND WHERE IT COMES FROM
----------------------------------------------------------------------
545 of the 801 `count_mismatch` findings - 68.0 percent - name a figure that
does appear in a summary-shaped line somewhere in that same transcript. That is
measured against a deliberately generous rule (any provenance counts), so it is
an UPPER bound, but it is not a small number and it is not hidden here.

506 of those 545 have a single cause: a suite is run with its output redirected
to a file, and the summary is read back by a SEPARATE `tail`, `cat` or `grep`
call, which is not a runner and is therefore not credited. See LIMITS.

THE 545 AND THE 506 ABOVE ARE THE PREVIOUS BUILD'S NUMBERS, kept because they
are what ONE-HOP REDIRECT CHAINING was built against. The chaining mechanism
is now implemented, with the six bars and their tests, and re-measured over the
same corpus by the same scoring rule - see MEASURED AFTER CHAINING below.

The predecessor's measured rate was 20.4 percent. This build is worse ON THAT
METRIC and better on the one the rebuild was for: the four laundered shapes that
refuted the predecessor are refused here, and no lexical bar can be bypassed
into crediting them. Both numbers belong in front of whoever rules on it.

MEASURED AFTER CHAINING, 2026-09-07
-----------------------------------
Re-measured over every fifth `*.jsonl` under this account's `.claude/projects`
tree - 317 of 1584 files, 94136 records - with BOTH builds run over the SAME
sample in the same pass, because that is the only comparison that means
anything:

                                  before chaining   with chaining
    local runs credited                      3346            3479
    CI summary lines credited                  18              44
    CI commands                               387             387
    count claims checked                     1927            1927
    count_mismatch findings                   348             274
    ci_green_without_fetch findings             9               9
    count_mismatch scored FALSE       223 (64.1pc)    152 (55.5pc)

Scored by the previous round's rule exactly: a `count_mismatch` is FALSE when the
number it names appears as a `passed` count in a summary-shaped line anywhere in
that same transcript under ANY provenance. That is deliberately generous, so it
is an UPPER bound both times.

THE PREVIOUS ROUND'S HEADLINE FIGURES DID NOT REPRODUCE, and that is reported
rather than smoothed over. It recorded 313 files and 254497 records for the same
recipe; every fifth `*.jsonl` yields 317 files and 94136 records here, and the
pre-chaining build scores 348 findings at 64.1 percent on it rather than 801 at
68.0 percent. The corpus is live and grows under the reader, but a 2.7x gap in
record count is not drift - the earlier sample was not the one this recipe
selects. The before/after column pair above is measured on one identical sample
and is the number to rule on; 68.0 percent is not comparable to 55.5 percent.

LIMITS - STATED, NOT HIDDEN
---------------------------
  - A COMPOUND COMMAND THAT MIXES A READER AND A RUNNER IS CREDITED WHOLE.
    `python -m pytest tests > out.txt; cat out.txt` is the project's own
    convention and must be credited; `cat docs/LEDGER.md && python -m pytest`
    therefore is too. Splitting credit per segment would need per-segment output
    attribution, which a transcript does not carry.
  - A SEPARATE `cat out.txt` CALL is credited ONLY through the one-hop rule
    above, and only when a RUNNER redirected into that exact path earlier in
    this same transcript and no non-runner has written to it since. `echo "930
    passed ... in 1s" > out.txt; cat out.txt` is still refused, because `echo`
    cannot seed. The residual is a write this file does not read as a write -
    `Out-File`, a program's own `-o` flag - landing in a seeded path.
  - A PYTHON ONE-LINER THAT ONLY PRINTS A FILE is classified a runner, because
    the head token cannot distinguish it from one that runs pytest.
  - `mcp__Desktop_Commander__interact_with_process` carries its text in `input`
    rather than `command`, so it classifies as neither. That is the safe
    direction and it is not guessed around.

OPEN, ASKED OF SIBLING-C ON 2026-09-07
--------------------------------------
Asked by cross-repo note; no reply at time of writing. Each is a GUESS here, made
in the conservative direction and isolated so it can be corrected in one place:

  - THE FULL FINDING TAXONOMY. `FINDING_NAMES` holds the two names that can each
    say something the other cannot. That sibling's taxonomy may be larger. No name is
    invented, because an invented name would reach ledgers and roadmaps and then
    have to be un-invented.
  - EXIT-CODE SEMANTICS. `BLOCK_EXIT_CODE = 2` mirrors the Claude Code hook
    convention where 2 blocks, but that has NOT been verified against this
    harness for the Stop event. Under the default `annotate` mode it is never
    used.
  - WHETHER THE GATE EVER BLOCKS A STOP. Unknown. Made a PARAMETER (`--mode`,
    `DEFAULT_MODE = "annotate"`) rather than baked into control flow, so
    adopting a blocking posture later is a flag change and not a rewrite.
  - THE STOP-HOOK STDIN KEY NAME. `TRANSCRIPT_PATH_KEY = "transcript_path"` is
    NOT verified against this harness. When stdin JSON lacks it the gate exits
    cleanly saying so rather than crashing.

FAIL-OPEN, NEVER FAIL-SILENT
----------------------------
A gate that dies is a gate that is off. A missing, unreadable, malformed or
partly-corrupt transcript produces a clean exit with a STATED reason on stdout,
never a traceback and never a silent pass.

This module writes no state and binds no port. `core/ports.py` owns every port
number in this repository and this file needs none.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# The closed contract
# ---------------------------------------------------------------------------

FINDING_NAMES: tuple[str, ...] = (
    "count_mismatch",
    "ci_green_without_fetch",
)

CLAIM_COUNT = "count"
CLAIM_CI_GREEN = "ci_green"

SOURCE_LOCAL = "local"
SOURCE_CI = "ci"
SOURCE_OTHER = "other"

DEFAULT_MODE = "annotate"
MODES: tuple[str, ...] = ("annotate", "block")

# UNVERIFIED against this harness - see OPEN above.
BLOCK_EXIT_CODE = 2
TRANSCRIPT_PATH_KEY = "transcript_path"

# The tools whose output a COMMAND produced. Everything else - a Read of a
# document, a Grep, an Agent report, a web fetch - is credited to neither list
# on tool name alone, before any command text is looked at.
LOCAL_SHELL_TOOLS: frozenset[str] = frozenset(
    {
        "Bash",
        "BashOutput",
        "PowerShell",
        "mcp__Desktop_Commander__start_process",
        "mcp__Desktop_Commander__interact_with_process",
        "mcp__Windows-MCP__PowerShell",
    }
)

WEB_FETCH_TOOLS: frozenset[str] = frozenset({"WebFetch", "WebSearch"})


# ---------------------------------------------------------------------------
# Command classification - the provenance rule
# ---------------------------------------------------------------------------

#: Shell separators. `&&` and `||` are listed before the single-character forms
#: so alternation does not split `&&` into two empty segments. A lone `&` is not
#: a separator here, because `2>&1` is not two commands.
_SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||;|\||\n|\r")

#: Quote-aware enough to keep `"C:/Program Files/py.exe" -m pytest` in one piece.
#: A regex rather than `shlex`, which raises on the unbalanced quotes that a
#: transcript line legitimately contains and would turn a parse into a crash.
_TOKEN_RE = re.compile(r'"[^"]*"|\'[^\']*\'|\S+')

_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

_NUMERIC_RE = re.compile(r"^\d+(?:\.\d+)?$")

#: Tokens that stand in FRONT of the real executable. Skipped while walking to
#: the head, so `timeout 900 python -m pytest` and PowerShell's
#: `& "<abs path>/python.exe" -m pytest` both resolve to an interpreter.
_LAUNCHERS: frozenset[str] = frozenset(
    {
        "&",
        "call",
        "command",
        "exec",
        "env",
        "nice",
        "nohup",
        "start",
        "stdbuf",
        "sudo",
        "time",
        "timeout",
        "winpty",
        "xargs",
        "xvfb-run",
    }
)

#: Executables that ARE a test runner by name.
_RUNNER_EXES: frozenset[str] = frozenset({"pytest", "py.test", "tox", "nox"})

#: Python interpreters. Widened past `pytest` deliberately - see the module
#: docstring. `py` is the Windows launcher; `python3.11`, `pythonw` and a bare
#: `python` all land here, and a `.exe` suffix and any directory are stripped
#: before the match.
_PY_EXE_RE = re.compile(r"^(?:python|pythonw)[0-9._]*$|^py(?:[0-9.]+)?$")

#: Used ONLY when the head token is a shell variable and therefore unresolvable.
_PYTEST_TOKEN_RE = re.compile(r"(?:^|\s)(?:-m\s+)?py\.?test(?:\s|$)", re.IGNORECASE)

# Anything that reads a CI run. `gh run list` is included: it reports CI status
# without a log, which is still a fetch for the purposes of
# `ci_green_without_fetch`, and it must never be mistaken for a local run.
#
# `gh` IS INVOKED BY ABSOLUTE PATH IN THIS FLEET, and a pattern requiring
# whitespace straight after `gh` missed every one of them. Measured on the real
# corpus: `"C:/Program Files/GitHub CLI/gh.exe" run view <id> --log` classified
# as neither CI nor local, so a session that HAD read CI was flagged for
# asserting CI green without a fetch. `_GH` absorbs the `.exe` and the closing
# quote that sit between the name and the subcommand.
_GH = r"\bgh(?:\.exe)?[\"']?\s+"

_CI_FETCH_RES: tuple[re.Pattern[str], ...] = (
    re.compile(_GH + r"run\s+(?:view|list|watch|download)\b", re.IGNORECASE),
    re.compile(_GH + r"workflow\s+(?:view|list|run)\b", re.IGNORECASE),
    re.compile(_GH + r"api\b[^\n]{0,200}?\bactions\b", re.IGNORECASE),
    re.compile(r"/actions/runs?\b", re.IGNORECASE),
)


def _normalise_exe(token: str) -> str:
    """A head token reduced to a bare lowercase program name.

    Strips one layer of quotes, both path separators, and a `.exe` suffix, so
    `"C:\\Users\\x\\Python314\\python.exe"` and `/usr/bin/python3.11` and
    `python` all reduce to something `_PY_EXE_RE` can answer.
    """
    name = token.strip().strip('"').strip("'")
    name = name.replace("\\", "/")
    name = name.rsplit("/", 1)[-1]
    if name.lower().endswith(".exe"):
        name = name[:-4]
    return name.lower()


def _segment_head(segment: str) -> str | None:
    """The executable a segment invokes, or None when it invokes nothing.

    Walks from the left past launchers, `VAR=value` assignments, option flags
    and bare numeric arguments. A segment that is only assignments - the
    `PY="<abs path>"` line this fleet writes before using `$PY` - has no head,
    and contributes nothing rather than being guessed at.
    """
    for token in _TOKEN_RE.findall(segment):
        if _ASSIGNMENT_RE.match(token) or _NUMERIC_RE.match(token):
            continue
        if token.startswith("-"):
            continue
        name = _normalise_exe(token)
        if name in _LAUNCHERS or name == "":
            continue
        return name
    return None


def _segment_is_runner(segment: str) -> bool:
    """Does this one segment EXECUTE code, as opposed to reading a file?"""
    head = _segment_head(segment)
    if head is None:
        return False
    if head in _RUNNER_EXES or _PY_EXE_RE.match(head):
        return True
    if "$" in head or "%" in head:
        # An unresolvable head - `& $py -m pytest`. This is the only case where
        # a `pytest` token elsewhere in the segment is allowed to decide, and it
        # is why `grep pytest docs/` is not caught by it: `grep` resolves.
        return bool(_PYTEST_TOKEN_RE.search(segment))
    return False


#: Shell redirection. `\d*>>?` takes `>`, `>>`, `1>` and `2>`; `&>` is the
#: bash both-streams form.
#:
#: `&` IS EXCLUDED FROM THE TARGET CHARACTER CLASS, and that exclusion is the
#: whole of what stops `2>&1` seeding a path called `&1` on every redirected run
#: in the corpus - `&1` is a file descriptor, not a file, and a bogus seed would
#: then be harvested by any later command whose text carried that token. A
#: guarding `(?![&|>])` lookahead was written here first and DELETED on
#: measurement: every character it refused is already outside the class, so no
#: mutation of it changed a single test. A rule whose mutant nothing catches is
#: dead code. `test_a_descriptor_dup_is_not_a_redirect_target` pins the
#: behaviour, and removing `&` from the class below is what makes it go red.
_REDIRECT_RE = re.compile(r"(?:\d*>>?|&>)\s*(\"[^\"]*\"|'[^']*'|[^\s;|&<>]+)")

#: `tee` and `tee -a`. Option flags are skipped so the FILE is what is captured.
#: A boundary before `tee` keeps it from matching inside a longer word.
_TEE_RE = re.compile(
    r"(?:^|[|;&\s])tee(?:\.exe)?\s+(?:-[A-Za-z-]+\s+)*(\"[^\"]*\"|'[^']*'|[^\s;|&<>]+)"
)


def normalise_path(token: str) -> str:
    """A path token reduced to one comparable form.

    Strips one layer of quotes, folds backslashes to forward slashes, drops a
    leading `./`, and lowercases. The lowercasing is deliberate and its cost is
    stated in the module docstring: this fleet runs on Windows, where two
    casings name one file, so treating them as one is the accurate model here.
    """
    name = token.strip().strip('"').strip("'")
    name = name.replace("\\", "/")
    while name.startswith("./"):
        name = name[2:]
    return name.rstrip("/").lower()


def redirect_targets(command: str) -> tuple[str, ...]:
    """Every path this command WRITES through shell redirection or `tee`.

    Shell redirection and `tee` only - see the module docstring. A program's own
    output flag is not read, so it neither seeds nor revokes, which is the safe
    direction in both cases: an unseen write cannot seed, and an unseen write to
    a path a runner seeded is the one residual this mechanism carries.
    """
    found: list[str] = []
    for pattern in (_REDIRECT_RE, _TEE_RE):
        for raw in pattern.findall(command):
            target = normalise_path(raw)
            if target and target not in found:
                found.append(target)
    return tuple(found)


def command_path_tokens(command: str) -> tuple[str, ...]:
    """The command's tokens, normalised as paths, in the order written.

    Matching a seeded path against whole TOKENS rather than as a substring is
    bar 5: `cat out.txt.bak` must not harvest the seed recorded for `out.txt`.
    """
    return tuple(normalise_path(token) for token in _TOKEN_RE.findall(command))


def _chain_source(
    command: str,
    source: str,
    seeded: dict[str, str],
    revoked: set[str],
) -> str:
    """Fold one command into the seed ledger and return its effective source.

    A runner's or CI reader's redirect targets are SEEDED, unless already
    revoked - bar 2 is permanent in both directions of order, so a genuine run
    cannot un-poison a path a non-runner has written.

    Any other command's redirect targets are REVOKED first, which is what makes
    `cat a.txt > b.txt` fail to pass the seed on (bar 3), and only then is the
    command tested for a read of a still-seeded path. CI wins over local when a
    command reads both, matching the direction `classify_command` already takes.
    """
    targets = redirect_targets(command)

    if source in (SOURCE_LOCAL, SOURCE_CI):
        for target in targets:
            if target not in revoked:
                seeded[target] = source
        return source

    for target in targets:
        revoked.add(target)
        seeded.pop(target, None)

    inherited = {seeded[token] for token in command_path_tokens(command) if token in seeded}
    if SOURCE_CI in inherited:
        return SOURCE_CI
    if SOURCE_LOCAL in inherited:
        return SOURCE_LOCAL
    return source


def classify_command(command: str) -> str:
    """CI reader, test runner, or neither - decided on the COMMAND TEXT.

    Order matters. A compound command that touches CI at all is CI: under-
    crediting a local run is recoverable, laundering a CI number as local is the
    defect this file exists to stop.

    Everything that is neither is `SOURCE_OTHER` and its output is never parsed.
    That is the whole provenance rule: `cat`, `grep`, `git log`, `head` and
    `find` return `SOURCE_OTHER`, so a count printed from a tracked file cannot
    become evidence no matter what shape the line takes.
    """
    for pattern in _CI_FETCH_RES:
        if pattern.search(command):
            return SOURCE_CI
    for segment in _SEGMENT_SPLIT_RE.split(command):
        if _segment_is_runner(segment):
            return SOURCE_LOCAL
    return SOURCE_OTHER


# ---------------------------------------------------------------------------
# Line-level parsing - shape only, and only for output a runner produced
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# `gh run view --log` emits "<job>\t<step>\t<ISO-8601 timestamp> <content>".
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\s+")

# Every word pytest can put in a terminal summary. An unknown word means that
# match is not a pytest summary and it is discarded, but the scan continues
# along the line - see `parse_summary_line`.
_COUNT_WORDS: frozenset[str] = frozenset(
    {
        "passed",
        "failed",
        "error",
        "errors",
        "skipped",
        "xfailed",
        "xpassed",
        "deselected",
        "warning",
        "warnings",
        "rerun",
        "reruns",
        # pytest-subtests. Its absence refused a real `19547 passed ... 4575
        # subtests passed in 177.97s` outright, because one unknown word
        # rejected the whole line.
        "subtests",
    }
)

#: `pytest-subtests` writes `4575 subtests passed`, the only TWO-word tally
#: pytest emits. The counts grammar takes one word per number, so the tally is
#: normalised to the one-word form rather than widening the grammar - a grammar
#: that accepted `N <word> <word>` would also accept prose.
_SUBTESTS_RE = re.compile(r"(\d+)\s+subtests\s+passed", re.IGNORECASE)

#: The terminal-summary shape, searched for ANYWHERE in the line rather than
#: anchored at its start. Anchoring was measured as the largest single source of
#: false positives: it refused every labelled run this project prints, and
#: labels are this project's own convention. Provenance is what refuses a stale
#: count now, so the anchor had nothing left to protect.
#:
#: The two lookarounds are the only boundaries kept. `(?<![\w.])` stops a match
#: starting mid-number, so `19547 passed` cannot also be read as `9547 passed`.
#: `(?![\w.])` stops `in 17.50seconds` from reading as a duration.
_SUMMARY_RE = re.compile(
    r"(?<![\w.])(?P<counts>\d+\s+[A-Za-z]+(?:\s*,\s*\d+\s+[A-Za-z]+)*)"
    r"\s+in\s+(?P<seconds>\d+(?:\.\d+)?)s(?![\w.])"
)

_PAIR_RE = re.compile(r"(\d+)\s+([A-Za-z]+)")

_CLAIM_COUNT_RE = re.compile(r"(\d+)\s+passed\b", re.IGNORECASE)

#: A CI-green CLAIM. `all checks passed` was here and is REMOVED: it is ruff's
#: literal terminal output, so every session that reported
#: `python -m ruff check .  All checks passed!` in a QA table was flagged for
#: asserting CI green without a fetch, with nothing to do with CI at all.
_CLAIM_CI_GREEN_RE = re.compile(
    r"\bCI\b[^.\n]{0,60}?\b(?:green|passing|passed|succeeded|success)\b"
    r"|\bworkflows?\b[^.\n]{0,40}?\bgreen\b",
    re.IGNORECASE,
)

#: The gate was negation-blind: "CI failed on my commit - local was green" was
#: read as a CI-green claim, because `CI` and `green` sat inside one 60-char
#: window. A sentence reporting CI FAILURE is the opposite of the claim being
#: audited, and flagging it is worse than missing it.
#:
#: `red` is NOT in this list, and its absence was measured rather than assumed -
#: see MEASURED in the module docstring. `red` describing a PAST state is how a
#: session narrates a recovery ("CI was red, it is green now"), and that
#: sentence is a green claim the gate should audit, not suppress.
_CI_NEGATION_RE = re.compile(
    r"\b(?:fail|failed|failing|failure|broke|broken|error|errored)\b",
    re.IGNORECASE,
)


def _clause_around(text: str, match: re.Match[str]) -> str:
    """The sentence the match sits in, for the negation test.

    Scoped to one clause rather than the whole record deliberately. A record
    that mentions a failure anywhere would otherwise suppress every CI-green
    claim in it, and a gate that stops firing because the text is long is a
    gate that is off.
    """
    start = max(text.rfind(".", 0, match.start()), text.rfind("\n", 0, match.start()))
    end = min(
        (pos for pos in (text.find(".", match.end()), text.find("\n", match.end())) if pos != -1),
        default=len(text),
    )
    return text[start + 1 : end]


@dataclass(frozen=True)
class SummaryLine:
    """One credited pytest terminal summary.

    `record_index` is the 1-based position among the records that PARSED, not
    the raw file line number - a malformed line contributes to
    `Evidence.malformed_lines` and shifts nothing.
    """

    passed: int
    failed: int
    skipped: int
    seconds: float
    record_index: int = 0


@dataclass(frozen=True)
class Claim:
    kind: str
    record_index: int
    number: int | None = None


@dataclass(frozen=True)
class Finding:
    """A report line. Carries NO transcript text - see the module docstring."""

    name: str
    record_index: int
    detail: str


@dataclass(frozen=True)
class CheckResult:
    """(checked, offenders), always both.

    Zero out of zero reads as a pass. A checker that matched nothing reports
    "0 offenders" and looks clean, so `checked` says whether it ARMED at all and
    is asserted before the offender list everywhere it is used.
    """

    name: str
    checked: int
    offenders: tuple[Finding, ...] = ()


@dataclass(frozen=True)
class Evidence:
    """What the transcript PROVES, split by provenance and never merged."""

    local_runs: tuple[SummaryLine, ...] = ()
    ci_fetches: tuple[SummaryLine, ...] = ()
    records_scanned: int = 0
    tool_results_scanned: int = 0
    malformed_lines: int = 0
    #: CI-reading COMMANDS that ran, which is not the same as CI summary lines
    #: parsed out of their output. `gh run list` reports status and prints no
    #: pytest summary, so it contributed nothing and `fetched_ci()` stayed
    #: False while the docstring said otherwise. Appended at the END with a
    #: default, because a mid-class required field breaks every positional
    #: construction.
    ci_commands: int = 0

    def ran_tests_locally(self) -> bool:
        return bool(self.local_runs)

    def fetched_ci(self) -> bool:
        """Did this session read CI at all - by command, not by parsed output.

        A fetch that returned no pytest summary is still a fetch. Crediting
        only parsed summaries made the check fire on sessions whose evidence
        was sitting in the transcript in a shape it declined to look at.
        """
        return bool(self.ci_fetches) or self.ci_commands > 0


@dataclass(frozen=True)
class GateReport:
    transcript: str
    evidence: Evidence
    claims: tuple[Claim, ...] = ()
    checks: tuple[CheckResult, ...] = ()
    reason: str = ""
    lines: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when nothing was flagged.

        A gate that could not run is `ok` AND carries a non-empty `reason`. The
        two are read together: `reason` is the honest statement that no
        measurement happened, and callers must not read `ok` alone.
        """
        return not any(check.offenders for check in self.checks)


def normalise_log_line(raw: str) -> str:
    """Reduce a raw output line to its content.

    Strips ANSI, the tab-separated job and step fields `gh run view --log`
    prepends, and the ISO-8601 timestamp after them. Everything downstream sees
    the same shape whether it came from a local shell or a CI log.
    """
    line = _ANSI_RE.sub("", raw)
    if "\t" in line:
        line = line.rsplit("\t", 1)[-1]
    line = _TIMESTAMP_RE.sub("", line.lstrip())
    return line.strip()


def parse_summary_line(raw: str, record_index: int = 0) -> SummaryLine | None:
    """Recognise a pytest terminal summary anywhere in one line, or refuse it.

    This function decides SHAPE ONLY. It does not decide whether the line is
    evidence - `build_evidence()` has already refused every line that did not
    come from a runner or a CI reader before this is called. Calling it on
    arbitrary text will happily parse a stale count out of a document, which is
    correct: it is a parser, not a gate.

    THE REQUIRED `in <float>s` DURATION IS THE ONE REFUSER LEFT. A tally without
    it is not a pytest terminal summary, and that is what keeps qa_companion's
    `16 passed, 0 failed, 2 skipped` from being read as a pytest count.

    A label before the counts and a suffix after the duration are both allowed.
    Every candidate is checked word by word, and a candidate carrying a word
    pytest never prints is discarded - but the scan CONTINUES along the line, so
    a line reading `Ran 5 modules in 3.0s; 930 passed in 17.5s` still yields the
    real summary instead of stopping at the first thing that looked close.
    """
    line = _SUBTESTS_RE.sub(r"\1 subtests", normalise_log_line(raw))

    for match in _SUMMARY_RE.finditer(line):
        counts: dict[str, int] = {}
        known = True
        for number, word in _PAIR_RE.findall(match.group("counts")):
            key = word.lower()
            if key not in _COUNT_WORDS:
                known = False
                break
            counts[key] = counts.get(key, 0) + int(number)
        if not known or "passed" not in counts:
            continue
        try:
            seconds = float(match.group("seconds"))
        except ValueError:  # pragma: no cover - the grammar already pinned it
            continue
        return SummaryLine(
            passed=counts["passed"],
            failed=counts.get("failed", 0) + counts.get("error", 0) + counts.get("errors", 0),
            skipped=counts.get("skipped", 0),
            seconds=seconds,
            record_index=record_index,
        )
    return None


def scan_summary_lines(text: str, record_index: int = 0) -> list[SummaryLine]:
    found = []
    for raw in text.splitlines():
        parsed = parse_summary_line(raw, record_index)
        if parsed is not None:
            found.append(parsed)
    return found


# ---------------------------------------------------------------------------
# Record walking
# ---------------------------------------------------------------------------


def _content_blocks(record: object) -> list[dict]:
    if not isinstance(record, dict):
        return []
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def _result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [str(part.get("text", "")) for part in content if isinstance(part, dict)]
        return "\n".join(parts)
    return ""


def _tool_source(name: str, tool_input: object) -> str:
    """Provenance for a tool_use, from its name and its input.

    A tool that is not a shell and not a web fetch is `SOURCE_OTHER` on its name
    alone, which is what makes a `Read` of a document, a `Grep` and an `Agent`
    report contribute nothing before any text is looked at.
    """
    inp = tool_input if isinstance(tool_input, dict) else {}
    if name in LOCAL_SHELL_TOOLS:
        return classify_command(str(inp.get("command", "")))
    if name in WEB_FETCH_TOOLS:
        url = str(inp.get("url", "")) + " " + str(inp.get("query", ""))
        return SOURCE_CI if classify_command(url) == SOURCE_CI else SOURCE_OTHER
    return SOURCE_OTHER


def build_evidence(records: list[dict], malformed_lines: int = 0) -> Evidence:
    """Walk the transcript once, forward, pairing tool_use to tool_result.

    A tool_result whose tool_use is not in the map - a truncated transcript, or
    output that arrived before its call - is credited to NEITHER list. Guessing
    its provenance is how a CI number becomes a local run.

    This is where provenance gates crediting: `scan_summary_lines()` is only
    ever reached for a result whose command classified as a runner or a CI
    reader, OR whose command reads back a path such a command redirected into
    earlier in this same transcript. Nothing else is parsed at all.

    THE SEED LEDGER IS LOCAL TO ONE WALK. `seeded` and `revoked` are built here
    and discarded here, so no state crosses transcripts and the forward walk is
    what makes bar 4 hold - a read cannot see a seed recorded after it.

    `ci_commands` counts commands classified CI on their OWN text. A chained
    read of a CI-seeded file is not counted again: the fetch that seeded it was
    already counted, and double-counting would make the number mean something
    other than what `Evidence.ci_commands` says it means.
    """
    sources: dict[str, str] = {}
    local: list[SummaryLine] = []
    ci: list[SummaryLine] = []
    results_seen = 0
    ci_commands = 0
    seeded: dict[str, str] = {}
    revoked: set[str] = set()

    for index, record in enumerate(records, start=1):
        for block in _content_blocks(record):
            kind = block.get("type")
            if kind == "tool_use":
                name = str(block.get("name", ""))
                raw_input = block.get("input")
                tagged = _tool_source(name, raw_input)
                if tagged == SOURCE_CI:
                    ci_commands += 1
                if name in LOCAL_SHELL_TOOLS:
                    inp = raw_input if isinstance(raw_input, dict) else {}
                    tagged = _chain_source(
                        str(inp.get("command", "")), tagged, seeded, revoked
                    )
                sources[str(block.get("id"))] = tagged
            elif kind == "tool_result":
                results_seen += 1
                source = sources.get(str(block.get("tool_use_id")), SOURCE_OTHER)
                if source == SOURCE_OTHER:
                    continue
                summaries = scan_summary_lines(_result_text(block), index)
                if source == SOURCE_LOCAL:
                    local.extend(summaries)
                else:
                    ci.extend(summaries)

    return Evidence(
        local_runs=tuple(local),
        ci_fetches=tuple(ci),
        ci_commands=ci_commands,
        records_scanned=len(records),
        tool_results_scanned=results_seen,
        malformed_lines=malformed_lines,
    )


def _assistant_text(record: object) -> str:
    if not isinstance(record, dict) or record.get("type") != "assistant":
        return ""
    message = record.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return str(message["content"])
    parts = [
        str(block.get("text", ""))
        for block in _content_blocks(record)
        if block.get("type") == "text"
    ]
    return "\n".join(parts)


def extract_claims(records: list[dict]) -> tuple[Claim, ...]:
    """Claims come from assistant TEXT only.

    Tool output is evidence, never a claim, and the assistant's own prose is a
    claim, never evidence. Crossing the two would let the report validate itself.
    """
    claims: list[Claim] = []
    for index, record in enumerate(records, start=1):
        text = _assistant_text(record)
        if not text:
            continue
        for match in _CLAIM_COUNT_RE.finditer(text):
            claims.append(Claim(kind=CLAIM_COUNT, record_index=index, number=int(match.group(1))))
        green = _CLAIM_CI_GREEN_RE.search(text)
        if green is not None and not _CI_NEGATION_RE.search(_clause_around(text, green)):
            claims.append(Claim(kind=CLAIM_CI_GREEN, record_index=index))
    return tuple(claims)


# ---------------------------------------------------------------------------
# The two checks
# ---------------------------------------------------------------------------


def credited_pass_counts(evidence: Evidence) -> set[int]:
    """The ONLY sanctioned union of the two lists - see the module docstring."""
    return {s.passed for s in evidence.local_runs} | {s.passed for s in evidence.ci_fetches}


def check_count_mismatch(claims: tuple[Claim, ...], evidence: Evidence) -> CheckResult:
    supported = credited_pass_counts(evidence)
    counted = [c for c in claims if c.kind == CLAIM_COUNT and c.number is not None]
    offenders = tuple(
        Finding(
            name="count_mismatch",
            record_index=claim.record_index,
            detail=(
                f"asserted {claim.number} passed; no credited terminal summary in this "
                f"transcript reports that count "
                f"(credited: {sorted(supported) if supported else 'none'})"
            ),
        )
        for claim in counted
        if claim.number not in supported
    )
    return CheckResult(name="count_mismatch", checked=len(counted), offenders=offenders)


def check_ci_green_without_fetch(claims: tuple[Claim, ...], evidence: Evidence) -> CheckResult:
    green = [c for c in claims if c.kind == CLAIM_CI_GREEN]
    offenders: tuple[Finding, ...] = ()
    if not evidence.fetched_ci():
        offenders = tuple(
            Finding(
                name="ci_green_without_fetch",
                record_index=claim.record_index,
                detail=(
                    "CI is asserted green but this transcript contains no credited CI "
                    "fetch - a local run does not substitute, the lists are separate"
                ),
            )
            for claim in green
        )
    return CheckResult(name="ci_green_without_fetch", checked=len(green), offenders=offenders)


_CHECKS = (check_count_mismatch, check_ci_green_without_fetch)


def run_checks(claims: tuple[Claim, ...], evidence: Evidence) -> tuple[CheckResult, ...]:
    results = tuple(check(claims, evidence) for check in _CHECKS)
    if tuple(r.name for r in results) != FINDING_NAMES:  # pragma: no cover - contract guard
        raise AssertionError("check order drifted from FINDING_NAMES")
    return results


# ---------------------------------------------------------------------------
# Loading - never crashes
# ---------------------------------------------------------------------------


def load_records(path: Path) -> tuple[list[dict], int, str]:
    """Return (records, malformed_lines, reason).

    A non-empty reason means nothing could be measured. It is stated, never
    swallowed: a gate that passes silently when it could not read its input is
    indistinguishable from one that is switched off.
    """
    try:
        if not path.exists():
            return [], 0, f"transcript not found at {path}, so no claim was checked"
        if path.is_dir():
            return [], 0, f"transcript path {path} is a directory, so no claim was checked"
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [], 0, f"transcript at {path} could not be read ({type(exc).__name__}), so no claim was checked"

    records: list[dict] = []
    malformed = 0
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
        else:
            malformed += 1
    return records, malformed, ""


def gate_transcript(path: Path) -> GateReport:
    records, malformed, reason = load_records(path)
    if reason:
        return GateReport(transcript=str(path), evidence=Evidence(), reason=reason)

    evidence = build_evidence(records, malformed_lines=malformed)
    claims = extract_claims(records)
    checks = run_checks(claims, evidence)
    return GateReport(transcript=str(path), evidence=evidence, claims=claims, checks=checks)


def format_report(report: GateReport) -> list[str]:
    if report.reason:
        return [f"stop-claim-gate: STOOD DOWN - {report.reason}"]

    evidence = report.evidence
    lines = [
        f"stop-claim-gate: {report.transcript}",
        (
            f"  scanned {evidence.records_scanned} record(s), "
            f"{evidence.tool_results_scanned} tool result(s), "
            f"{evidence.malformed_lines} malformed line(s)"
        ),
        (
            f"  evidence: {len(evidence.local_runs)} local run(s), "
            f"{len(evidence.ci_fetches)} CI summary line(s), "
            f"{evidence.ci_commands} CI command(s) - counted separately"
        ),
        f"  claims: {len(report.claims)}",
    ]
    for check in report.checks:
        lines.append(f"  {check.name}: checked {check.checked}, flagged {len(check.offenders)}")
        for finding in check.offenders:
            lines.append(f"    record {finding.record_index}: {finding.detail}")
    if report.ok:
        lines.append("  no findings")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stop_claim_gate",
        description="Check a session's report claims against the transcript's own evidence.",
    )
    parser.add_argument("--transcript", help="path to a session transcript JSONL")
    parser.add_argument(
        "--mode",
        choices=MODES,
        default=DEFAULT_MODE,
        help="annotate (default) reports and exits 0; block exits non-zero on any finding",
    )
    args = parser.parse_args(argv)

    if args.transcript:
        path: Path | None = Path(args.transcript)
        stdin_reason = ""
    else:
        path, stdin_reason = _transcript_from_stdin()

    if path is None:
        print(f"stop-claim-gate: STOOD DOWN - {stdin_reason}")
        return 0

    report = gate_transcript(path)
    for line in format_report(report):
        print(line)

    if args.mode == "block" and not report.ok:
        return BLOCK_EXIT_CODE
    return 0


def _transcript_from_stdin() -> tuple[Path | None, str]:
    """Read the Stop-hook payload, or say why it could not be used.

    `TRANSCRIPT_PATH_KEY` is NOT verified against this harness - see OPEN in the
    module docstring. Every failure below is a clean stand-down.
    """
    stream = sys.stdin
    try:
        if stream is None or stream.isatty():
            return None, (
                "no --transcript given and stdin is a terminal, so there is no "
                f"{TRANSCRIPT_PATH_KEY} to read"
            )
        raw = stream.read()
    except (OSError, ValueError) as exc:
        return None, (
            f"no --transcript given and stdin could not be read ({type(exc).__name__}), "
            f"so no {TRANSCRIPT_PATH_KEY} was available"
        )

    if not raw.strip():
        return None, f"no --transcript given and stdin was empty, so no {TRANSCRIPT_PATH_KEY} was available"

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None, (
            "no --transcript given and stdin was not JSON, so no "
            f"{TRANSCRIPT_PATH_KEY} could be taken from it"
        )

    if not isinstance(payload, dict):
        return None, f"stdin JSON was not an object, so it carries no {TRANSCRIPT_PATH_KEY}"

    value = payload.get(TRANSCRIPT_PATH_KEY)
    if not isinstance(value, str) or not value:
        return None, (
            f"stdin JSON carried no usable {TRANSCRIPT_PATH_KEY} key; the key name is "
            "unverified against this harness, so the gate stands down rather than guessing"
        )
    return Path(value), ""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
