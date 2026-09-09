"""The pre-push gate REQUESTS skip reporting from both pytest invocations.

WHY THIS EXISTS, MEASURED.

Under a real `git push` the pre-push hook's `tests` suite reports 2 skips where
the same command in an interactive shell reports 1. Naming the second one took a
push to a scratch bare repository under a scratch `core.hooksPath`; it is
`tests/test_hook_interpreter.py:1774`, and it is CORRECT. Git prepends
`mingw64/libexec/git-core` to PATH for its own hooks, so `shutil.which("git")`
resolves to a `git.exe` under `git-core`, which is not an install root, and that
arm skips.

A GATE THAT CAN SEE A SKIP AND CANNOT SAY WHICH ONE IS THE DEFECT. The hook must
therefore ask pytest to list its skips, so the operator reads the module and
line rather than a bare count.

GENERALISES: the pre-push hook runs with a PATH that is not your shell's, so any
arm keyed on RESOLVING a tool answers a different question there.

WHAT THIS MODULE CAN AND CANNOT SEE - the ceiling, stated plainly.

The proposition asserted here is narrow and deliberate: BOTH pytest invocations
in the hook REQUEST SKIP REPORTING. Nothing weaker, nothing stronger.

  - It is a TOKEN SCAN OF A SHELL LINE, not a shell parse. Logical lines are
    rejoined across a trailing backslash and comment lines are dropped, and that
    is the whole of the shell semantics modelled. A `case`, an `eval`, an alias,
    a sourced fragment or a variable holding a flag would all be invisible.
  - It CANNOT know what `$TEST_PY` expands to, so it cannot know that the thing
    invoked is a python at all, only that the line asks `-m pytest`.
  - It does NOT assert invocation ORDER. Order is not the claim, and a reorder of
    two independent suites is a correct hook.
  - It reads only the `-r` SPEC and decides from its characters. `-rs`, `-rA`,
    `-ra`, `-rsx` and `-rfsE` all report skips; `-rf` alone does not. An earlier
    attempt at this file keyed on the literal `-rs` and went RED for `-rA`, which
    is strictly MORE reporting - a false red on a correct hook, which is the
    dominant defect class in this tree.
  - NOTHING HERE INSPECTS HOOK OUTPUT. No arm runs the hook and reads what it
    printed. `tests/test_hook_interpreter.py` does run the real hook but STUBS
    pytest, so it would not catch the flag's removal either. Whether the gate's
    OUTPUT ever gets inspected is OPEN.

THREE DISPOSITIONS, and the third is not a failure. Hook present with skip
reporting -> PASS. Hook present WITHOUT it -> FAIL. Hook ABSENT -> SKIP naming
absence, because a `git archive` extract or a partial checkout legitimately has
no `.githooks/`, and reddening there is a false red about a file that is not
missing from the repository, only from this copy.
"""
from __future__ import annotations

import shlex
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The hook under audit. A MODULE ATTRIBUTE on purpose: an adversarial harness
#: repoints it at a mutated scratch copy to prove these arms are not vacuous,
#: without touching the tracked file while a suite may be running.
HOOK_PATH = REPO_ROOT / ".githooks" / "pre-push"

#: The two suite targets `pytest.ini` mandates be run SEPARATELY. Typed here by
#: hand rather than read out of the hook: a census that reads its own answer from
#: the file it audits is not a census.
EXPECTED_TARGETS = ("tests", "agents/pity_engine")

#: `-r` spec characters that cause pytest to list skipped tests. `s` is skips
#: outright; `a` is "all except passed" and `A` is "all", and both include skips.
#: `f`, `E`, `x`, `X`, `p` and `P` do not.
SKIP_REPORTING_CHARS = frozenset("saA")


def _hook_text() -> str:
    """The hook's bytes as ASCII text, or SKIP when the hook is not present.

    Absence is the third disposition and is reported as a skip with a TRUE reason
    naming the missing path. Every arm in this module routes through here, so no
    arm can pass while the hook is absent.
    """
    if not HOOK_PATH.exists():
        pytest.skip(
            f"{HOOK_PATH} is not present in this copy of the repository, so what the "
            "pre-push gate asks pytest for cannot be established and this guard is "
            "SKIPPED rather than passed - that is the normal state of a `git archive` "
            "extract or a partial checkout"
        )
    return HOOK_PATH.read_bytes().decode("ascii")


def _logical_lines(text: str) -> list[str]:
    """Rejoin shell continuation lines and drop comments.

    This is the ENTIRE extent of the shell modelling. See the module docstring.
    """
    out: list[str] = []
    pending = ""
    for raw in text.split("\n"):
        line = raw.rstrip("\r")
        if pending:
            pending = pending + " " + line.strip()
        else:
            if line.lstrip().startswith("#"):
                continue
            pending = line
        if pending.rstrip().endswith("\\"):
            pending = pending.rstrip()[:-1].rstrip()
            continue
        out.append(pending)
        pending = ""
    if pending:
        out.append(pending)
    return out


def parse_pytest_invocations(text: str) -> list[tuple[str, str]]:
    """Every `-m pytest` invocation in `text` as (target, r_spec).

    `target` is the first non-option operand after `pytest`, slash-normalised.
    `r_spec` is the concatenation of every `-r` argument seen, whether attached
    (`-rsx`) or detached (`-r s`). An invocation with no `-r` yields "".
    """
    found: list[tuple[str, str]] = []
    for line in _logical_lines(text):
        try:
            tokens = shlex.split(line, comments=True, posix=True)
        except ValueError:
            continue
        for start in range(len(tokens) - 1):
            if tokens[start] != "-m" or tokens[start + 1] != "pytest":
                continue
            spec = ""
            target = ""
            i = start + 2
            while i < len(tokens):
                tok = tokens[i]
                if tok in ("||", "&&", ";", "|", "&"):
                    break
                if tok == "-r" and i + 1 < len(tokens):
                    spec += tokens[i + 1]
                    i += 2
                    continue
                if tok.startswith("-r") and len(tok) > 2:
                    spec += tok[2:]
                    i += 1
                    continue
                if tok.startswith("-"):
                    i += 1
                    continue
                if not target:
                    target = tok.replace("\\", "/")
                i += 1
            found.append((target, spec))
    return found


def spec_reports_skips(r_spec: str) -> bool:
    """Does this `-r` spec make pytest list skipped tests by module and line."""
    return any(char in SKIP_REPORTING_CHARS for char in r_spec)


def test_the_hook_invokes_both_suites_separately() -> None:
    """The gate runs `tests` and `agents/pity_engine`, each as its own command.

    This arm is what makes a COMMENTED-OUT suite block a failure rather than a
    vacuous pass: "every invocation requests skip reporting" is trivially true of
    zero invocations, so the count and the targets are pinned here.
    """
    invocations = parse_pytest_invocations(_hook_text())
    targets = sorted(target for target, _ in invocations)
    assert targets == sorted(EXPECTED_TARGETS), (
        f"the pre-push gate must invoke exactly {sorted(EXPECTED_TARGETS)} as separate "
        f"pytest commands; the token scan of {HOOK_PATH} found {targets}"
    )


def test_every_pytest_invocation_requests_skip_reporting() -> None:
    """Both invocations ask pytest to NAME its skips, not merely count them.

    Any `-r` spec containing s, a or A satisfies this. `-rA` is a pass here and
    was a false red in the attempt this file replaces.
    """
    invocations = parse_pytest_invocations(_hook_text())
    assert invocations, f"no `-m pytest` invocation found in {HOOK_PATH} at all"
    silent = [(target, spec) for target, spec in invocations if not spec_reports_skips(spec)]
    assert not silent, (
        "the pre-push gate can see a skip and cannot say WHICH ONE for "
        f"{[t for t, _ in silent]}: their `-r` specs are {[s for _, s in silent]!r}, and "
        "none of those characters lists skips. Add s, a or A to the `-r` spec - under a "
        "real push this suite reports 2 skips where a shell reports 1, and the second is "
        "tests/test_hook_interpreter.py"
    )


def test_the_hook_records_why_skip_reporting_is_required() -> None:
    """A reader of the hook is told WHY the flag is there, and it is load-bearing.

    NOT a bare substring search. The previous attempt's comment arm was exactly
    that and PASSED with the flag deleted from both invocations, which is a lie
    about the hook. This arm therefore asserts BOTH halves - the prose and the
    behaviour - so deleting the flag reddens it too.
    """
    text = _hook_text()
    invocations = parse_pytest_invocations(text)
    assert invocations and all(spec_reports_skips(spec) for _, spec in invocations), (
        "the comment explaining skip reporting is only worth grading while the flag it "
        f"explains is actually present; the `-r` specs found are {invocations!r}"
    )
    comments = "\n".join(line for line in text.split("\n") if line.lstrip().startswith("#"))
    assert "test_hook_interpreter" in comments, (
        "the hook must NAME the second skip a real push produces - "
        "tests/test_hook_interpreter.py - because an unnamed skip is the defect this "
        f"flag exists to remove. The comment block in {HOOK_PATH} does not mention it"
    )
    assert "PATH" in comments, (
        "the hook must record the ROOT CAUSE: git prepends git-core to PATH for its "
        "hooks, so any arm keyed on resolving a tool answers a different question here. "
        f"No comment in {HOOK_PATH} mentions PATH"
    )


def test_the_spec_reader_accepts_every_reporting_form_and_rejects_the_rest() -> None:
    """Non-vacuity for the parser itself, against shapes the real hook lacks.

    A CONTROL THAT ONLY PLANTS THE CASE THE MATCHER HANDLES CANNOT DISCOVER THAT
    THE MATCHER IS NARROW, so the accept side carries five spellings and the
    reject side carries the specs that genuinely do not list skips.
    """
    assert parse_pytest_invocations(_hook_text()), (
        f"the parser found nothing in the real {HOOK_PATH}, so the synthetic cases below "
        "would be grading a parser that does not work on the artifact"
    )
    for spec in ("s", "A", "a", "sx", "fsE"):
        assert spec_reports_skips(spec), f"-r{spec} does list skips and must be accepted"
    for spec in ("", "f", "E", "xX", "fEp"):
        assert not spec_reports_skips(spec), f"-r{spec} does NOT list skips and must be rejected"


def test_a_detached_r_spec_and_a_continuation_line_are_both_read() -> None:
    """`-r s` and a backslash-split invocation are correct hooks, not failures.

    Both were false reds in the attempt this file replaces. Asserted against
    synthetic lines because the real hook uses neither shape - and the real hook
    is parsed first so this is not grading a parser detached from the artifact.
    """
    assert parse_pytest_invocations(_hook_text()), f"the parser found nothing in {HOOK_PATH}"
    detached = parse_pytest_invocations('"$TEST_PY" -m pytest -r s tests || exit 1')
    assert detached == [("tests", "s")], f"a detached -r spec was misread: {detached!r}"
    continued = parse_pytest_invocations('"$TEST_PY" -m pytest -rs \\\n    tests || exit 1')
    assert continued == [("tests", "s")], f"a continuation line was misread: {continued!r}"


def test_the_hook_is_lf_only_ascii() -> None:
    """No CR bytes and no byte above 0x7f - the hook is a POSIX sh script.

    A CR in a `sh` script is a syntax error on the shebang line, and this tree
    pins `eol=lf` in `.gitattributes` precisely because `write_text` on Windows
    would introduce one invisibly.
    """
    if not HOOK_PATH.exists():
        _hook_text()
    raw = HOOK_PATH.read_bytes()
    assert b"\r" not in raw, f"{HOOK_PATH} contains CR bytes - a sh script must be LF-only"
    high = sorted({byte for byte in raw if byte > 0x7F})
    assert not high, f"{HOOK_PATH} is not 7-bit ASCII; offending byte values: {high}"
