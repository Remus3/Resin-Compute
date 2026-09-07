"""Guards for tools/stop_claim_gate.py - the session CLAIM gate.

This tree gates the ARTIFACT at SessionStart, pre-commit and pre-push. Nothing
gated the REPORT. Three prose-falsity findings in recent sessions were caught by
a human read rather than by a check.

THE THESIS THESE TESTS EXIST TO FALSIFY
---------------------------------------
Crediting is decided by PROVENANCE, not by the shape of a line. `parse_summary_line`
is a parser and will happily read a count out of a document; `build_evidence` is
the gate, and it never shows the parser anything a runner or a CI reader did not
print. The load-bearing arms are the paired ones: the SAME BYTES arriving from a
`cat`, a `grep`, a `git log` or a `Read` credit nothing, and arriving from
`python -m pytest` credit normally. If provenance ever stops deciding, those
pairs go red together.

WHAT EVERY TEST HERE HAS TO DO, and why the shape is not decorative:

  1. ASSERT THE CHECKED COUNT BEFORE THE OFFENDER LIST. Zero out of zero reads
     as a pass. A checker that matched nothing reports "0 offenders" and looks
     clean, so `checked` is asserted first in every case.

  2. EVERY HAPPY-PATH TEST ESTABLISHES THE PRECONDITION THAT ARMS THE CHECK IT
     ASSERTS ABOUT. Sibling-C published this exact failure: their
     happy-path test had no runs in the transcript, so the count check never
     armed, and asserting "nothing was flagged" went green while proving
     nothing.

  3. EVERY REFUSAL IS PAIRED WITH AN ACCEPTANCE. Without a positive control, a
     gate that refuses everything passes both refusal tests.

Fixtures are hand-built JSONL. They carry an invented operator identity - never
a real Windows account name, home path or sibling repository root.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from tools import stop_claim_gate as gate

# ---------------------------------------------------------------------------
# Observed ground truth, measured 2026-09-07 against 313 real transcripts and
# against this repository's own suite output. These strings are DATA, quoted so
# a reader can see what shape is credited.
# ---------------------------------------------------------------------------

REAL_LOCAL_SUMMARY = "930 passed, 1 skipped in 17.50s"
REAL_FAILED_FIRST_SUMMARY = "1 failed, 63 passed in 0.38s"
REAL_SHORT_SUMMARY = "80 passed in 4.58s"

# This project's own conventions. Because an exit code read through a pipe is
# the pipe's, sessions here write `cmd > file` and label what they report; and
# the mutation harnesses print a tally with a suffix after the duration. All
# four were REFUSED by the previous lexical bar and all four are real runs.
LABELLED_SUMMARY = "full-suite run 1 EXIT=0  841 passed, 1 skipped in 14.64s"
SUFFIXED_SUMMARY = "tests/data/test_locate.py                28 passed in 0.07s           exit=0"
MUTANT_SUMMARY = "MUT a_neuter_heal: exit=1 tail=3 failed, 8 passed in 0.63s"
SUBTESTS_SUMMARY = (
    "2 failed, 19547 passed, 144 skipped, 1 warning, 4575 subtests passed in 177.97s (0:02:57)"
)

# tools/qa_companion.py prints its own tally. It is NOT a pytest terminal
# summary - there is no "in <float>s" - and crediting it would launder a number
# no pytest run produced. This is the ONE lexical refuser that survives.
QA_COMPANION_TALLY = "  16 passed, 0 failed, 2 skipped"

# The four shapes two adversarial passes used to launder a count past the old
# lexical bar. Each is a perfectly-shaped summary; each is refused now because
# of WHERE it comes from, not what it looks like.
ASPIRATIONAL = "target: " + REAL_LOCAL_SUMMARY
STALE = "stale: " + REAL_LOCAL_SUMMARY
GREP_OUTPUT = "docs/LEDGER.md:12:  " + REAL_LOCAL_SUMMARY
COMMENTED = "# stale historical:\t" + REAL_LOCAL_SUMMARY

# A line as `gh run view <id> --log` actually emits it: job, tab, step, tab,
# ISO-8601 timestamp, then the content.
CI_LOG_PREFIX = "build\tRun the suites\t2026-09-07T03:52:52.1234567Z "

LOCAL_PYTEST_CMD = 'cd "/srv/example-tree" && python -m pytest tests'
CI_FETCH_CMD = 'cd "/srv/example-tree" && gh run view 34084946425 --log'
# `gh` by absolute path, with the `.exe` and the closing quote between the name
# and the subcommand. Measured on the real corpus; the old pattern missed it.
CI_FETCH_ABSOLUTE_CMD = 'cd "/srv/example-tree" && "C:/Tools/GitHub CLI/gh.exe" run view 31874678071 --log'
INVENTED_PYTHON = '"C:/Tools/py311/python.exe"'


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _assistant_text(text: str) -> dict:
    return {
        "type": "assistant",
        "sessionId": "00000000-0000-4000-8000-000000000000",
        "cwd": "/srv/example-tree",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def _tool_use(tool_id: str, name: str, **inp: object) -> dict:
    return {
        "type": "assistant",
        "sessionId": "00000000-0000-4000-8000-000000000000",
        "message": {
            "role": "assistant",
            "content": [{"type": "tool_use", "id": tool_id, "name": name, "input": inp}],
        },
    }


def _tool_result(tool_id: str, output: str) -> dict:
    return {
        "type": "user",
        "sessionId": "00000000-0000-4000-8000-000000000000",
        "message": {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tool_id, "content": output, "is_error": False}
            ],
        },
    }


def _local_run(tool_id: str, output: str) -> list[dict]:
    return [_tool_use(tool_id, "Bash", command=LOCAL_PYTEST_CMD), _tool_result(tool_id, output)]


def _ci_fetch(tool_id: str, output: str) -> list[dict]:
    return [_tool_use(tool_id, "Bash", command=CI_FETCH_CMD), _tool_result(tool_id, output)]


def _via(tool_id: str, command: str, output: str) -> list[dict]:
    """One Bash call carrying `output`, so provenance is the only variable."""
    return [_tool_use(tool_id, "Bash", command=command), _tool_result(tool_id, output)]


def _write_transcript(tmp_path: Path, records: list[dict], name: str = "session.jsonl") -> Path:
    """Write JSONL as BYTES.

    `Path.write_text` converts LF to CRLF on Windows and `read_text` hides it,
    and `.gitattributes eol=lf` hides it from the diff as well. Bytes are the
    only honest way to pin what is on disk.
    """
    payload = "".join(json.dumps(rec) + "\n" for rec in records)
    target = tmp_path / name
    target.write_bytes(payload.encode("utf-8"))
    return target


# ---------------------------------------------------------------------------
# PROVENANCE - the rebuild's thesis, pinned behaviourally
# ---------------------------------------------------------------------------

READER_COMMANDS = [
    "cat docs/LEDGER.md",
    'grep -rn "passed" docs/',
    "git log --oneline -20",
    "head -40 docs/LEDGER.md",
    "tail -5 notes.txt",
    "find . -name '*.md'",
]


@pytest.mark.parametrize("command", READER_COMMANDS)
def test_a_reader_command_credits_nothing_however_perfect_the_line(command):
    """The whole slice, in one arm.

    Each of these prints a byte-perfect terminal summary and none of them ran a
    test. The paired acceptance is the test below, which sends the SAME BYTES
    through pytest and requires them credited - so this is provenance refusing,
    not a gate that refuses everything.
    """
    evidence = gate.build_evidence(_via("toolu_read", command, REAL_LOCAL_SUMMARY))

    assert evidence.tool_results_scanned == 1, "precondition: the result was actually walked"
    assert evidence.local_runs == ()
    assert evidence.ci_fetches == ()


def test_the_same_bytes_from_a_test_runner_are_credited_normally():
    """ACCEPTANCE for every refusal above. Provenance is the ONLY difference."""
    evidence = gate.build_evidence(_via("toolu_run", LOCAL_PYTEST_CMD, REAL_LOCAL_SUMMARY))

    assert evidence.tool_results_scanned == 1
    assert [s.passed for s in evidence.local_runs] == [930]


def test_a_read_of_a_document_credits_nothing_but_the_shell_arm_does():
    """A stale count inside a tracked doc must not become evidence.

    Both arms in one test so the pair cannot drift apart.
    """
    payload = "....\n" + REAL_LOCAL_SUMMARY + "\n"

    doc = gate.build_evidence(
        [
            _tool_use("toolu_read", "Read", file_path="/srv/example-tree/docs/LEDGER.md"),
            _tool_result("toolu_read", payload),
        ]
    )
    assert doc.tool_results_scanned == 1
    assert doc.local_runs == ()
    assert doc.ci_fetches == ()

    shell = gate.build_evidence(_local_run("toolu_sh", payload))
    assert shell.tool_results_scanned == 1
    assert [s.passed for s in shell.local_runs] == [930]


@pytest.mark.parametrize("line", [ASPIRATIONAL, STALE, GREP_OUTPUT, COMMENTED])
def test_the_four_laundered_shapes_are_refused_by_provenance_not_by_shape(line):
    """The four lines two adversarial passes got credited.

    Each PARSES - that is asserted here, not hidden - and each is refused
    anyway, because a `cat` printed it. Asserting the parse is the point: it
    proves the refusal comes from provenance, so tightening the grammar again
    could not be what is doing the work.
    """
    assert gate.parse_summary_line(line) is not None, "the parser still reads the shape"

    evidence = gate.build_evidence(_via("toolu_cat", "cat docs/LEDGER.md", line))
    assert evidence.tool_results_scanned == 1
    assert evidence.local_runs == ()


def test_parse_summary_line_is_a_parser_and_says_so():
    """Non-vacuity for the test above.

    If `parse_summary_line` ever started refusing on shape again, the four
    laundering arms would pass for the wrong reason.
    """
    assert gate.parse_summary_line(GREP_OUTPUT) is not None
    assert gate.parse_summary_line(COMMENTED) is not None


# ---------------------------------------------------------------------------
# classify_command - runner, CI reader, or neither
# ---------------------------------------------------------------------------

RUNNER_COMMANDS = [
    "python -m pytest tests",
    LOCAL_PYTEST_CMD,
    "pytest tests/test_thing.py",
    "py.test -x",
    "tox -e py311",
    "nox -s tests",
    "timeout 900 python -m pytest tests",
    INVENTED_PYTHON + " -m pytest tests",
    "PYTHONPATH=. python -m pytest tests",
    "python -m unittest discover",
    'python "/srv/example-tree/scratch/mutate.py"',
]


@pytest.mark.parametrize("command", RUNNER_COMMANDS)
def test_a_runner_command_classifies_local(command):
    assert gate.classify_command(command) == gate.SOURCE_LOCAL


@pytest.mark.parametrize("command", READER_COMMANDS)
def test_a_reader_command_classifies_as_neither(command):
    assert gate.classify_command(command) == gate.SOURCE_OTHER


def test_a_powershell_call_through_a_variable_is_a_runner():
    """The head cannot be resolved, so the `pytest` token decides - and ONLY
    then. The paired arm below is what stops that fallback becoming a hole."""
    assert gate.classify_command("$py = 'x'; & $py -m pytest tests") == gate.SOURCE_LOCAL


def test_grepping_for_the_word_pytest_is_not_running_pytest():
    """The fallback above must not fire when the head IS resolvable.

    Without this, `grep pytest docs/` would be read as a run and the whole
    provenance rule would leak through its own escape hatch.
    """
    assert gate.classify_command("grep -rn pytest docs/") == gate.SOURCE_OTHER
    assert gate.classify_command("cat pytest.ini") == gate.SOURCE_OTHER


def test_an_assignment_only_command_invokes_nothing():
    assert gate.classify_command('PY="/srv/example-tree/py"') == gate.SOURCE_OTHER
    assert gate.classify_command("") == gate.SOURCE_OTHER


def test_classify_command_separates_a_ci_fetch_from_a_local_run():
    assert gate.classify_command(CI_FETCH_CMD) == gate.SOURCE_CI
    assert gate.classify_command(LOCAL_PYTEST_CMD) == gate.SOURCE_LOCAL
    assert gate.classify_command("gh run list --branch main --limit 2") == gate.SOURCE_CI


def test_gh_invoked_by_absolute_path_is_still_a_ci_fetch():
    """Measured on the real corpus: the fleet calls `gh` by full path.

    A pattern that required whitespace straight after `gh` matched none of
    them, so sessions that HAD read CI were flagged for asserting CI green
    without a fetch. The bare-name arm is the paired control.
    """
    assert gate.classify_command(CI_FETCH_ABSOLUTE_CMD) == gate.SOURCE_CI
    assert gate.classify_command('"C:/Tools/GitHub CLI/gh.exe" run list') == gate.SOURCE_CI
    assert gate.classify_command("gh run view 1 --log") == gate.SOURCE_CI


def test_a_compound_command_that_touches_ci_is_never_credited_as_local():
    """Conservative by design - under-credit local rather than launder CI."""
    compound = "gh run view 1 --log > out.txt && python -m pytest tests"
    assert gate.classify_command(compound) == gate.SOURCE_CI


# ---------------------------------------------------------------------------
# parse_summary_line - SHAPE ONLY. The duration is the one refuser left.
# ---------------------------------------------------------------------------


def test_parse_summary_line_credits_a_real_local_pytest_summary():
    parsed = gate.parse_summary_line(REAL_LOCAL_SUMMARY)
    assert parsed is not None
    assert parsed.passed == 930
    assert parsed.skipped == 1
    assert parsed.failed == 0


def test_parse_summary_line_credits_a_failed_first_summary():
    """pytest puts failures FIRST. A passed-anchored regex would miss this."""
    parsed = gate.parse_summary_line(REAL_FAILED_FIRST_SUMMARY)
    assert parsed is not None
    assert parsed.passed == 63
    assert parsed.failed == 1


def test_parse_summary_line_credits_a_decorated_summary():
    """Without -q pytest wraps the summary in `=` rules."""
    parsed = gate.parse_summary_line("========== " + REAL_SHORT_SUMMARY + " ===========")
    assert parsed is not None
    assert parsed.passed == 80


def test_a_label_before_the_counts_is_credited():
    """This project's own convention, refused by the previous `^` anchor."""
    parsed = gate.parse_summary_line(LABELLED_SUMMARY)
    assert parsed is not None
    assert parsed.passed == 841
    assert parsed.skipped == 1


def test_a_trailing_suffix_after_the_duration_is_credited():
    parsed = gate.parse_summary_line(SUFFIXED_SUMMARY)
    assert parsed is not None
    assert parsed.passed == 28


def test_a_mutation_harness_line_is_credited():
    """`exit=1 tail=3 failed, 8 passed in 0.63s` - the counts start mid-line and
    a non-count word sits immediately before them."""
    parsed = gate.parse_summary_line(MUTANT_SUMMARY)
    assert parsed is not None
    assert parsed.passed == 8
    assert parsed.failed == 3


def test_a_subtests_summary_is_credited():
    parsed = gate.parse_summary_line(SUBTESTS_SUMMARY)
    assert parsed is not None
    assert parsed.passed == 19547
    assert parsed.failed == 2
    assert parsed.skipped == 144


def test_parse_summary_line_refuses_a_tally_with_no_duration():
    """qa_companion's own tally has counts but no `in <float>s`.

    THE ONE LEXICAL REFUSER LEFT, so it carries its own acceptance control.
    """
    assert gate.parse_summary_line(QA_COMPANION_TALLY) is None
    assert gate.parse_summary_line("23607 passed") is None

    accepted = gate.parse_summary_line("23607 passed, 258 skipped in 1182.00s")
    assert accepted is not None
    assert accepted.passed == 23607


def test_an_unknown_count_word_discards_that_match_but_not_the_line():
    """A tally pytest never prints is not a summary - but the scan continues.

    Refusing the whole line on the first bad candidate is how a real summary
    printed after a near-miss went uncredited.
    """
    assert gate.parse_summary_line("Ran 5 modules in 3.00s") is None

    both = gate.parse_summary_line("Ran 5 modules in 3.00s; " + REAL_LOCAL_SUMMARY)
    assert both is not None, "the real summary after the near-miss must survive"
    assert both.passed == 930


def test_the_grammar_cannot_start_matching_mid_number():
    """A count must not be read out of the tail of a longer token.

    Pins the left lookaround, and it takes the VERSION-STRING case to do it:
    with `19547 passed` the leftmost match is the whole number either way, so
    that arm alone leaves the lookaround untested. `v1.930` is where the two
    behaviours diverge - without the lookaround a version number becomes a
    pass count.
    """
    assert gate.parse_summary_line("build v1.930 passed in 17.50s") is None

    labelled = gate.parse_summary_line("build 930 passed in 17.50s")
    assert labelled is not None, "the same line without the version prefix must credit"
    assert labelled.passed == 930

    parsed = gate.parse_summary_line("19547 passed in 10.00s")
    assert parsed is not None
    assert parsed.passed == 19547


def test_a_comment_marker_no_longer_refuses_a_line():
    """The deleted comment bar, pinned ABSENT.

    Measured over 313 real transcripts: reinstating a `#`-anywhere refusal
    moved credited local runs from 5572 to 5571 and changed 0 findings. It was
    also trivially bypassed - `normalise_log_line` keeps only what follows the
    last tab, so `# stale historical:<TAB>930 passed ...` reached the old bar
    with the marker already stripped. Provenance is what refuses a commented
    count now, and this arm goes red if a shape-based bar creeps back.
    """
    assert gate.normalise_log_line(COMMENTED) == REAL_LOCAL_SUMMARY, (
        "the tab-strip is why a comment bar never saw the marker"
    )
    assert gate.parse_summary_line("      # 930 passed, 1 skipped in 17.50s") is not None


def test_a_word_glued_to_the_duration_is_not_a_duration():
    """Pins the right lookaround."""
    assert gate.parse_summary_line("930 passed in 17.50seconds") is None
    assert gate.parse_summary_line("930 passed in 17.50s") is not None


def test_parse_summary_line_strips_a_ci_log_prefix_before_crediting():
    parsed = gate.parse_summary_line(CI_LOG_PREFIX + REAL_LOCAL_SUMMARY)
    assert parsed is not None
    assert parsed.passed == 930


# ---------------------------------------------------------------------------
# build_evidence - the two lists that must never be merged
# ---------------------------------------------------------------------------


def test_build_evidence_keeps_local_runs_and_ci_fetches_separate():
    records = [
        *_local_run("toolu_local", "....\n" + REAL_LOCAL_SUMMARY + "\n"),
        *_ci_fetch("toolu_ci", CI_LOG_PREFIX + "23607 passed, 258 skipped in 1182.00s\n"),
    ]
    evidence = gate.build_evidence(records)

    assert evidence.records_scanned == len(records)
    assert evidence.tool_results_scanned == 2
    assert [s.passed for s in evidence.local_runs] == [930]
    assert [s.passed for s in evidence.ci_fetches] == [23607]


def test_a_ci_only_session_has_no_local_runs():
    """The merge defect, guarded structurally.

    Folding the two lists would make "this session ran tests" true for a
    session that fetched a CI log and ran nothing.
    """
    records = _ci_fetch("toolu_ci", CI_LOG_PREFIX + REAL_LOCAL_SUMMARY + "\n")
    evidence = gate.build_evidence(records)

    assert evidence.tool_results_scanned == 1
    assert evidence.local_runs == ()
    assert len(evidence.ci_fetches) == 1
    assert evidence.ran_tests_locally() is False
    assert evidence.fetched_ci() is True


def test_a_ci_command_that_prints_no_summary_still_counts_as_a_fetch():
    """`gh run list` reports status and prints no pytest summary.

    Crediting only PARSED summaries left `fetched_ci()` False for sessions that
    had plainly read CI. The paired arm is a session that read nothing.
    """
    read_ci = gate.build_evidence(
        _via("toolu_ci", "gh run list --branch main --limit 3", "completed  success  tier1")
    )
    assert read_ci.ci_fetches == (), "precondition: no summary line was parsed out of it"
    assert read_ci.ci_commands == 1
    assert read_ci.fetched_ci() is True

    read_nothing = gate.build_evidence(_local_run("toolu_local", REAL_LOCAL_SUMMARY))
    assert read_nothing.ci_commands == 0
    assert read_nothing.fetched_ci() is False


def test_an_orphan_tool_result_is_credited_to_neither_list():
    evidence = gate.build_evidence([_tool_result("toolu_missing", REAL_LOCAL_SUMMARY)])
    assert evidence.tool_results_scanned == 1
    assert evidence.local_runs == ()
    assert evidence.ci_fetches == ()


def test_an_empty_transcript_reports_zero_scanned():
    """Non-vacuity of the scan itself.

    If `records_scanned` did not distinguish an empty transcript from a full
    one, every "no offenders" assertion in this file would be worthless.
    """
    evidence = gate.build_evidence([])
    assert evidence.records_scanned == 0
    assert evidence.tool_results_scanned == 0


# ---------------------------------------------------------------------------
# extract_claims
# ---------------------------------------------------------------------------


def test_extract_claims_reads_assistant_text_only():
    records = [
        _assistant_text("Both suites green: " + REAL_LOCAL_SUMMARY + "."),
        *_local_run("toolu_local", REAL_LOCAL_SUMMARY),
    ]
    claims = gate.extract_claims(records)
    counts = [c for c in claims if c.kind == gate.CLAIM_COUNT]

    assert len(counts) == 1, "the tool_result must not be mistaken for a claim"
    assert counts[0].number == 930


def test_extract_claims_finds_a_ci_green_assertion():
    claims = gate.extract_claims([_assistant_text("CI is green on main.")])
    assert [c.kind for c in claims] == [gate.CLAIM_CI_GREEN]


def test_a_sentence_reporting_ci_failure_is_not_a_ci_green_claim():
    """The negation guard, with its acceptance control alongside."""
    failing = gate.extract_claims(
        [_assistant_text("CI failed on my commit - the local suite was green.")]
    )
    assert [c.kind for c in failing] == []

    passing = gate.extract_claims([_assistant_text("CI is green on my commit.")])
    assert [c.kind for c in passing] == [gate.CLAIM_CI_GREEN]


def test_the_word_red_describing_a_past_state_does_not_suppress_a_green_claim():
    """MEASURED, not assumed - see MEASURED in the module docstring.

    `red` is the only negation word present in 8 CI-green clauses across the
    real corpus, and 7 of the 8 are genuine claims narrating a recovery. Putting
    `red` back in the negation set turns the guard against the claims it exists
    to audit, and this arm goes red when someone does.
    """
    claims = gate.extract_claims(
        [_assistant_text("CI on main is green, so nothing is inherited-red")]
    )
    assert [c.kind for c in claims] == [gate.CLAIM_CI_GREEN]


# ---------------------------------------------------------------------------
# count_mismatch
# ---------------------------------------------------------------------------


def test_count_mismatch_fires_on_a_number_no_evidence_supports():
    records = [
        *_local_run("toolu_local", REAL_LOCAL_SUMMARY),
        _assistant_text("All 931 passed."),
    ]
    evidence = gate.build_evidence(records)
    claims = gate.extract_claims(records)
    result = gate.check_count_mismatch(claims, evidence)

    assert result.checked == 1
    assert [f.name for f in result.offenders] == ["count_mismatch"]


def test_count_mismatch_is_silent_when_the_number_matches_a_local_run():
    """ACCEPTANCE, with the arming precondition asserted explicitly."""
    records = [
        *_local_run("toolu_local", "....\n" + REAL_LOCAL_SUMMARY + "\n"),
        _assistant_text("Reporting " + REAL_LOCAL_SUMMARY + "."),
    ]
    evidence = gate.build_evidence(records)
    claims = gate.extract_claims(records)
    result = gate.check_count_mismatch(claims, evidence)

    assert [s.passed for s in evidence.local_runs] == [930], "precondition: real evidence exists"
    assert result.checked == 1, "precondition: a count claim must exist for the check to arm"
    assert result.offenders == ()


def test_count_mismatch_accepts_a_number_supported_only_by_a_ci_fetch():
    records = [
        *_ci_fetch("toolu_ci", CI_LOG_PREFIX + "23607 passed, 258 skipped in 1182.00s"),
        _assistant_text("CI reports 23607 passed."),
    ]
    evidence = gate.build_evidence(records)
    claims = gate.extract_claims(records)
    result = gate.check_count_mismatch(claims, evidence)

    assert [s.passed for s in evidence.ci_fetches] == [23607], "precondition: CI evidence exists"
    assert result.checked == 1
    assert result.offenders == ()


def test_count_mismatch_fires_on_a_number_only_a_document_carried():
    """End to end over the defect this rebuild exists to close.

    The number is printed, byte-perfect, in the transcript - by `cat`. The claim
    is still flagged, because reading a file is not running a suite.
    """
    records = [
        *_via("toolu_cat", "cat docs/LEDGER.md", REAL_LOCAL_SUMMARY),
        _assistant_text("Reporting 930 passed."),
    ]
    evidence = gate.build_evidence(records)
    claims = gate.extract_claims(records)
    result = gate.check_count_mismatch(claims, evidence)

    assert evidence.local_runs == (), "the document must not have become evidence"
    assert result.checked == 1
    assert [f.name for f in result.offenders] == ["count_mismatch"]


# ---------------------------------------------------------------------------
# ci_green_without_fetch
# ---------------------------------------------------------------------------


def test_ci_green_without_fetch_fires_when_no_ci_log_was_read():
    records = [
        *_local_run("toolu_local", REAL_LOCAL_SUMMARY),
        _assistant_text("CI is green."),
    ]
    evidence = gate.build_evidence(records)
    claims = gate.extract_claims(records)
    result = gate.check_ci_green_without_fetch(claims, evidence)

    assert result.checked == 1
    assert [f.name for f in result.offenders] == ["ci_green_without_fetch"]


def test_ci_green_without_fetch_is_silent_after_a_real_fetch():
    """ACCEPTANCE, with the arming precondition asserted explicitly."""
    records = [
        *_ci_fetch("toolu_ci", CI_LOG_PREFIX + REAL_LOCAL_SUMMARY),
        _assistant_text("CI is green."),
    ]
    evidence = gate.build_evidence(records)
    claims = gate.extract_claims(records)
    result = gate.check_ci_green_without_fetch(claims, evidence)

    assert evidence.fetched_ci() is True, "precondition: a CI fetch must be present"
    assert result.checked == 1, "precondition: a CI-green claim must exist for the check to arm"
    assert result.offenders == ()


def test_ci_green_without_fetch_is_silent_after_a_full_path_gh_fetch():
    """The corpus shape. Without the absolute-path pattern this went red."""
    records = [
        *_via("toolu_ci", CI_FETCH_ABSOLUTE_CMD, "completed  success"),
        _assistant_text("CI is green."),
    ]
    evidence = gate.build_evidence(records)
    claims = gate.extract_claims(records)
    result = gate.check_ci_green_without_fetch(claims, evidence)

    assert evidence.ci_commands == 1, "precondition: the fetch must have been recognised"
    assert result.checked == 1
    assert result.offenders == ()


# ---------------------------------------------------------------------------
# Finding taxonomy is closed - and one name was DELETED
# ---------------------------------------------------------------------------


def test_the_finding_taxonomy_is_exactly_the_two_named_names():
    assert gate.FINDING_NAMES == ("count_mismatch", "ci_green_without_fetch")


def test_the_deleted_third_finding_has_not_come_back():
    """`tests_pass_without_run` armed only when every evidence list was empty,
    which made every count claim a `count_mismatch` as well - so its offender
    set is a strict subset of another check's by construction.

    Measured against this evidence model over 313 real transcripts: it would arm
    on 3172 claims, emit 3 findings, and 0 of those 3 name a record
    `count_mismatch` had not already flagged.

    A sweep needs a guard that the LEGITIMATE neighbours survived, which is what
    the three assertions below the first one are for.
    """
    assert "tests_pass_without_run" not in gate.FINDING_NAMES
    assert not hasattr(gate, "check_tests_pass_without_run")
    assert not hasattr(gate, "_drop_duplicate_findings")

    assert hasattr(gate, "check_count_mismatch")
    assert hasattr(gate, "check_ci_green_without_fetch")


def test_run_checks_returns_one_result_per_finding_name():
    records = [_assistant_text("930 passed and CI is green.")]
    results = gate.run_checks(gate.extract_claims(records), gate.build_evidence(records))
    assert tuple(r.name for r in results) == gate.FINDING_NAMES
    assert any(r.checked > 0 for r in results), "precondition: at least one check ARMED"


# ---------------------------------------------------------------------------
# Robustness - a gate that dies is a gate that is off
# ---------------------------------------------------------------------------


def test_a_malformed_line_is_counted_and_does_not_crash(tmp_path):
    target = tmp_path / "broken.jsonl"
    good = json.dumps(_assistant_text("930 passed."))
    target.write_bytes(("{not json at all\n" + good + "\n[]\n").encode("utf-8"))

    report = gate.gate_transcript(target)
    assert report.reason == ""
    assert report.evidence.malformed_lines == 2
    assert report.evidence.records_scanned == 1


def test_an_empty_file_is_measured_as_empty_rather_than_crashing(tmp_path):
    target = tmp_path / "empty.jsonl"
    target.write_bytes(b"")
    report = gate.gate_transcript(target)
    assert report.reason == ""
    assert report.evidence.records_scanned == 0
    assert report.ok is True


def test_binary_bytes_are_survived(tmp_path):
    target = tmp_path / "binary.jsonl"
    target.write_bytes(bytes(range(256)) * 16)
    report = gate.gate_transcript(target)
    assert report.reason == ""
    assert report.evidence.records_scanned == 0


def test_a_utf8_bom_does_not_defeat_the_first_record(tmp_path):
    target = tmp_path / "bom.jsonl"
    body = json.dumps(_local_run("toolu_local", REAL_LOCAL_SUMMARY)[0])
    second = json.dumps(_local_run("toolu_local", REAL_LOCAL_SUMMARY)[1])
    target.write_bytes(b"\xef\xbb\xbf" + (body + "\n" + second + "\n").encode("utf-8"))

    report = gate.gate_transcript(target)
    assert report.reason == ""
    assert report.evidence.records_scanned >= 1


def test_a_transcript_with_no_assistant_turns_finds_nothing_and_says_so(tmp_path):
    target = _write_transcript(tmp_path, _local_run("toolu_local", REAL_LOCAL_SUMMARY))
    report = gate.gate_transcript(target)

    assert report.evidence.local_runs, "precondition: the run was still credited"
    assert report.claims == ()
    assert all(c.checked == 0 for c in report.checks), "no claims means nothing armed"
    assert report.ok is True


def test_the_gate_survives_non_ascii_transcript_content(tmp_path):
    """The glyph is built with chr().

    Typing an em-dash into this file would make the test violate the 7-bit rule
    it exists alongside.
    """
    em_dash = chr(0x2014)
    smart_quote = chr(0x201C)
    text = "930 passed " + em_dash + " " + smart_quote + "green" + chr(0x201D)
    target = _write_transcript(tmp_path, [_assistant_text(text)])

    report = gate.gate_transcript(target)
    assert report.reason == ""
    assert report.evidence.records_scanned == 1


def test_a_missing_transcript_exits_cleanly_with_a_stated_reason(tmp_path):
    report = gate.gate_transcript(tmp_path / "nope.jsonl")
    assert report.reason != "", "a gate that cannot run must SAY so, not pass silently"
    assert report.ok is True


def test_a_directory_given_as_a_transcript_exits_cleanly(tmp_path):
    report = gate.gate_transcript(tmp_path)
    assert report.reason != ""
    assert report.ok is True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_main_reads_an_explicit_transcript_path(tmp_path, capsys):
    records = [
        *_local_run("toolu_local", REAL_LOCAL_SUMMARY),
        _assistant_text("Reporting " + REAL_LOCAL_SUMMARY + "."),
    ]
    target = _write_transcript(tmp_path, records)

    assert gate.main(["--transcript", str(target)]) == 0
    out = capsys.readouterr().out
    assert "no findings" in out.lower()


def test_main_takes_the_transcript_path_from_stdin_json(tmp_path, monkeypatch, capsys):
    target = _write_transcript(tmp_path, [_assistant_text("930 passed.")])
    payload = json.dumps({"transcript_path": str(target), "hook_event_name": "Stop"})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    assert gate.main([]) == 0
    assert "count_mismatch" in capsys.readouterr().out


def test_main_exits_cleanly_when_stdin_json_lacks_the_key(monkeypatch, capsys):
    """The key name is UNVERIFIED against this harness.

    If it is wrong the gate must say so and stand down, never crash.
    """
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"hook_event_name": "Stop"})))
    assert gate.main([]) == 0
    assert "transcript_path" in capsys.readouterr().out


def test_main_exits_cleanly_on_unparseable_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))
    assert gate.main([]) == 0
    assert capsys.readouterr().out.strip() != ""


def test_annotate_is_the_default_mode_and_never_blocks(tmp_path):
    target = _write_transcript(tmp_path, [_assistant_text("930 passed and CI is green.")])
    assert gate.DEFAULT_MODE == "annotate"
    assert gate.main(["--transcript", str(target)]) == 0


def test_block_mode_exits_nonzero_on_a_finding(tmp_path):
    target = _write_transcript(tmp_path, [_assistant_text("930 passed and CI is green.")])
    assert gate.main(["--transcript", str(target), "--mode", "block"]) == gate.BLOCK_EXIT_CODE
    assert gate.BLOCK_EXIT_CODE != 0


def test_block_mode_exits_zero_on_a_clean_transcript(tmp_path):
    """Positive control for block mode.

    Without it, a gate that blocked unconditionally would pass the test above.
    """
    records = [
        *_local_run("toolu_local", REAL_LOCAL_SUMMARY),
        _assistant_text("Reporting " + REAL_LOCAL_SUMMARY + "."),
    ]
    target = _write_transcript(tmp_path, records)
    report = gate.gate_transcript(target)

    assert report.evidence.local_runs, "precondition: real evidence exists"
    assert any(r.checked > 0 for r in report.checks), "precondition: at least one check ARMED"
    assert gate.main(["--transcript", str(target), "--mode", "block"]) == 0


# ---------------------------------------------------------------------------
# The gate must not publish what it caught
# ---------------------------------------------------------------------------


def test_a_finding_never_echoes_transcript_text(tmp_path):
    marker = "SENSITIVE-PROSE-THAT-MUST-NOT-BE-REPUBLISHED"
    records = [_assistant_text("930 passed. " + marker + ". CI is green.")]
    report = gate.gate_transcript(_write_transcript(tmp_path, records))

    offenders = [f for r in report.checks for f in r.offenders]
    assert offenders, "precondition: the transcript must actually produce findings"
    for finding in offenders:
        assert marker not in finding.detail
        assert marker not in repr(finding)


def test_a_finding_locates_itself_by_record_index(tmp_path):
    records = [_assistant_text("nothing here"), _assistant_text("930 passed.")]
    report = gate.gate_transcript(_write_transcript(tmp_path, records))

    offenders = [f for r in report.checks for f in r.offenders]
    assert offenders
    assert all(f.record_index == 2 for f in offenders)


# ---------------------------------------------------------------------------
# ONE-HOP REDIRECT CHAINING
#
# The motivating shape is this project's own standing convention. Because an
# exit code read through a pipe is the pipe's, sessions here redirect a suite to
# a file and read the code from the command rather than from a pipeline:
#
#     python -m pytest tests > out.txt 2>&1
#     echo "exit=$?"
#     tail -2 out.txt
#
# The suite really ran and its summary really is in the transcript, but the
# command that PRINTED the summary is `tail`, which is not a runner. Measured
# over 313 real transcripts: 506 of the 545 false positives the previous build
# shipped with are exactly this one shape.
#
# Six bars stop the hop re-opening the laundering surface the provenance rule
# closed. Every bar below carries its own refusal arm AND its own paired
# acceptance, because without a positive control a mechanism that chains NOTHING
# passes every refusal arm here while proving nothing.
# ---------------------------------------------------------------------------

SEEDED_PATH = "/srv/example-tree/build/out.txt"
#: Same basename, different directory. Bar 5.
OTHER_DIR_PATH = "/srv/example-tree/logs/out.txt"
FORGED_SUMMARY = "999 passed, 0 skipped in 1.00s"


def _redirected_run(tool_id: str, path: str = SEEDED_PATH) -> list[dict]:
    """A runner whose OWN result is empty, because its output went to a file."""
    return _via(tool_id, "python -m pytest tests > " + path + " 2>&1", "")


def _read_back(tool_id: str, path: str, output: str) -> list[dict]:
    return _via(tool_id, "tail -2 " + path, output)


def test_the_read_back_of_a_runner_redirect_is_credited_and_a_cold_read_is_not():
    """The whole slice in one arm, with the refusal it must not become."""
    chained = gate.build_evidence(
        [
            *_redirected_run("toolu_run"),
            *_read_back("toolu_tail", SEEDED_PATH, REAL_LOCAL_SUMMARY),
        ]
    )
    assert chained.tool_results_scanned == 2, "precondition: both results were walked"
    assert [s.passed for s in chained.local_runs] == [930]

    cold = gate.build_evidence(_read_back("toolu_tail", SEEDED_PATH, REAL_LOCAL_SUMMARY))
    assert cold.tool_results_scanned == 1
    assert cold.local_runs == (), "a tail of a path no runner ever seeded credits nothing"


NON_RUNNER_SEEDS = [
    'echo "' + REAL_LOCAL_SUMMARY + '" > ' + SEEDED_PATH,
    "cp docs/LEDGER.md " + SEEDED_PATH,
    "grep -rn passed docs/ > " + SEEDED_PATH,
    "cat docs/LEDGER.md >> " + SEEDED_PATH,
]


@pytest.mark.parametrize("command", NON_RUNNER_SEEDS)
def test_bar_one_only_a_runner_can_seed_a_path(command):
    """BAR 1. The seeding command must ITSELF be a runner.

    `echo "930 passed ... in 17.50s" > out.txt` followed by `cat out.txt` is the
    laundering shape the previous build refused outright, and it must stay
    refused. So must a `cp`, and so must any redirection by a command classified
    `other`.
    """
    evidence = gate.build_evidence(
        [
            *_via("toolu_seed", command, ""),
            *_via("toolu_cat", "cat " + SEEDED_PATH, REAL_LOCAL_SUMMARY),
        ]
    )
    assert evidence.tool_results_scanned == 2
    assert evidence.local_runs == ()
    assert evidence.ci_fetches == ()


def test_bar_one_acceptance_a_runner_redirect_does_seed_the_same_path():
    """Positive control for every arm above. Only the SEEDING command differs."""
    evidence = gate.build_evidence(
        [
            *_redirected_run("toolu_run"),
            *_via("toolu_cat", "cat " + SEEDED_PATH, REAL_LOCAL_SUMMARY),
        ]
    )
    assert evidence.tool_results_scanned == 2
    assert [s.passed for s in evidence.local_runs] == [930]


def test_bar_two_a_non_runner_write_revokes_the_seed():
    """BAR 2. `pytest > f` then `echo ... >> f` then `cat f` credits NOTHING.

    Not even the genuine line, because once the two share a file they cannot be
    told apart. Revoking is the safe direction; keeping the earlier credit is
    not.
    """
    forged_and_real = FORGED_SUMMARY + "\n" + REAL_LOCAL_SUMMARY

    poisoned = gate.build_evidence(
        [
            *_redirected_run("toolu_run"),
            *_via("toolu_echo", 'echo "' + FORGED_SUMMARY + '" >> ' + SEEDED_PATH, ""),
            *_read_back("toolu_tail", SEEDED_PATH, forged_and_real),
        ]
    )
    assert poisoned.tool_results_scanned == 3
    assert poisoned.local_runs == ()

    clean = gate.build_evidence(
        [
            *_redirected_run("toolu_run"),
            *_read_back("toolu_tail", SEEDED_PATH, forged_and_real),
        ]
    )
    assert [s.passed for s in clean.local_runs] == [999, 930], (
        "precondition: the SAME BYTES credit when nothing appended to the file"
    )


def test_bar_two_revocation_is_permanent_for_the_whole_transcript():
    """A later genuine redirect cannot un-poison a path a non-runner wrote."""
    evidence = gate.build_evidence(
        [
            *_via("toolu_echo", 'echo "' + FORGED_SUMMARY + '" >> ' + SEEDED_PATH, ""),
            *_redirected_run("toolu_run"),
            *_read_back("toolu_tail", SEEDED_PATH, REAL_LOCAL_SUMMARY),
        ]
    )
    assert evidence.tool_results_scanned == 3
    assert evidence.local_runs == ()


def test_bar_three_a_copy_made_by_a_non_runner_does_not_inherit_the_seed():
    """BAR 3. No second hop. `pytest > a` then `cat a > b` then `cat b`."""
    second = "/srv/example-tree/build/b.txt"

    evidence = gate.build_evidence(
        [
            *_redirected_run("toolu_run"),
            *_via("toolu_copy", "cat " + SEEDED_PATH + " > " + second, ""),
            *_via("toolu_read_b", "cat " + second, REAL_LOCAL_SUMMARY),
        ]
    )
    assert evidence.tool_results_scanned == 3
    assert evidence.local_runs == (), "the second hop must not credit"

    one_hop = gate.build_evidence(
        [
            *_redirected_run("toolu_run"),
            *_via("toolu_read_a", "cat " + SEEDED_PATH, REAL_LOCAL_SUMMARY),
        ]
    )
    assert [s.passed for s in one_hop.local_runs] == [930], (
        "precondition: the FIRST hop still credits, so this is depth refusing"
    )


def test_bar_four_a_read_before_the_seed_credits_nothing():
    """BAR 4. Evidence cannot flow backwards."""
    before = gate.build_evidence(
        [
            *_read_back("toolu_early", SEEDED_PATH, REAL_LOCAL_SUMMARY),
            *_redirected_run("toolu_run"),
        ]
    )
    assert before.tool_results_scanned == 2
    assert before.local_runs == ()

    after = gate.build_evidence(
        [
            *_redirected_run("toolu_run"),
            *_read_back("toolu_late", SEEDED_PATH, REAL_LOCAL_SUMMARY),
        ]
    )
    assert [s.passed for s in after.local_runs] == [930], (
        "precondition: the same read AFTER the seed credits, so order is what refused"
    )


def test_bar_five_the_seed_is_per_path_and_not_per_basename():
    """BAR 5. Two directories' `out.txt` are two paths."""
    assert Path(SEEDED_PATH).name == Path(OTHER_DIR_PATH).name, "precondition: same basename"

    crossed = gate.build_evidence(
        [
            *_redirected_run("toolu_run", SEEDED_PATH),
            *_read_back("toolu_tail", OTHER_DIR_PATH, REAL_LOCAL_SUMMARY),
        ]
    )
    assert crossed.tool_results_scanned == 2
    assert crossed.local_runs == ()

    same = gate.build_evidence(
        [
            *_redirected_run("toolu_run", SEEDED_PATH),
            *_read_back("toolu_tail", SEEDED_PATH, REAL_LOCAL_SUMMARY),
        ]
    )
    assert [s.passed for s in same.local_runs] == [930]


def test_bar_five_a_reader_of_a_longer_name_does_not_harvest_the_seed():
    """A seeded path must be matched as a TOKEN, never as a substring."""
    evidence = gate.build_evidence(
        [
            *_redirected_run("toolu_run"),
            *_via("toolu_cat", "cat " + SEEDED_PATH + ".bak", REAL_LOCAL_SUMMARY),
        ]
    )
    assert evidence.tool_results_scanned == 2
    assert evidence.local_runs == ()


def test_bar_six_a_ci_redirect_seeds_the_ci_list_and_never_the_local_one():
    """BAR 6. Folding the lists makes "this session ran tests" true for a
    session that only fetched a CI log - the defect Sibling-C published."""
    ci = gate.build_evidence(
        [
            *_via("toolu_ci", "gh run view 1 --log > " + SEEDED_PATH, ""),
            *_via("toolu_cat", "cat " + SEEDED_PATH, CI_LOG_PREFIX + REAL_LOCAL_SUMMARY),
        ]
    )
    assert ci.tool_results_scanned == 2
    assert [s.passed for s in ci.ci_fetches] == [930]
    assert ci.local_runs == ()
    assert ci.ran_tests_locally() is False, "a CI log read back is still not a local run"

    local = gate.build_evidence(
        [
            *_redirected_run("toolu_run"),
            *_via("toolu_cat", "cat " + SEEDED_PATH, REAL_LOCAL_SUMMARY),
        ]
    )
    assert [s.passed for s in local.local_runs] == [930]
    assert local.ci_fetches == (), "the hop does not merge the two lists either"


def test_a_read_of_both_a_ci_seed_and_a_local_seed_is_credited_ci():
    """The conservative direction `classify_command` already takes.

    Under-crediting a local run is recoverable; laundering a CI number as local
    is the defect this file exists to stop. The single-seed arms above are the
    controls that stop this being a gate that says CI to everything.
    """
    ci_path = "/srv/example-tree/build/ci.txt"
    both = gate.build_evidence(
        [
            *_via("toolu_ci", "gh run view 1 --log > " + ci_path, ""),
            *_redirected_run("toolu_run", SEEDED_PATH),
            *_via("toolu_cat", "cat " + SEEDED_PATH + " " + ci_path, REAL_LOCAL_SUMMARY),
        ]
    )
    assert both.tool_results_scanned == 3
    assert [s.passed for s in both.ci_fetches] == [930]
    assert both.local_runs == ()


REDIRECT_SHAPES = [
    ("python -m pytest tests > out.txt", "out.txt"),
    ("python -m pytest tests >> out.txt", "out.txt"),
    ("python -m pytest tests >out.txt", "out.txt"),
    ("python -m pytest tests > out.txt 2>&1", "out.txt"),
    ("python -m pytest tests 2>&1 > out.txt", "out.txt"),
    ("python -m pytest tests 1> out.txt", "out.txt"),
    ("python -m pytest tests &> out.txt", "out.txt"),
    ('python -m pytest tests > "my logs/out.txt"', "my logs/out.txt"),
    ("python -m pytest tests | tee out.txt", "out.txt"),
    ("python -m pytest tests | tee -a out.txt", "out.txt"),
]


@pytest.mark.parametrize("command,target", REDIRECT_SHAPES)
def test_redirect_targets_reads_every_shape_this_tree_writes(command, target):
    assert gate.redirect_targets(command) == (gate.normalise_path(target),)


def test_a_descriptor_dup_is_not_a_redirect_target():
    """`2>&1` is not a file, and `&1` must never become a seeded path.

    Without this the gate would seed `&1` on every redirected run and then
    credit any later command whose text carried that token.
    """
    assert gate.redirect_targets("python -m pytest tests 2>&1") == ()
    assert gate.redirect_targets("python -m pytest tests") == ()
    assert gate.redirect_targets("cat out.txt") == ()


def test_the_chaining_limits_are_recorded_in_the_module_docstring():
    """A guard that overstates its reach is worse than a missing one."""
    doc = gate.__doc__ or ""
    assert "ONE-HOP REDIRECT CHAINING" in doc
    assert "A BARE RELATIVE PATH CANNOT BE DISAMBIGUATED" in doc


def test_node_test_output_carries_no_line_the_summary_parser_would_credit():
    """Measured against real `node --test` output on this machine, 2026-09-07.

    `cd shell && node --test` is one of this repository's gates and
    `classify_command` returns `other` for it. That costs nothing: node's
    terminal summary is `pass 52` and `duration_ms 148.6112` - word before
    number, and no `in <float>s` duration - so the parser credits none of it and
    the classifier is not wrong. If node ever changes shape, this arm goes red.
    """
    node_summary = (
        "ok 52 - the tooltip is fixed text\n"
        "1..52\n"
        "# tests 52\n"
        "# suites 0\n"
        "# pass 52\n"
        "# fail 0\n"
        "# cancelled 0\n"
        "# skipped 0\n"
        "# todo 0\n"
        "# duration_ms 148.6112\n"
    )
    assert gate.scan_summary_lines(node_summary) == []
    assert gate.classify_command("cd shell && node --test") == gate.SOURCE_OTHER


# ---------------------------------------------------------------------------
# The module's own bytes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", [gate])
def test_the_gate_module_is_seven_bit_ascii(module):
    source = Path(module.__file__).read_bytes()
    assert len(source) > 0, "non-vacuity: an empty file is trivially ASCII"
    offending = [i for i, b in enumerate(source) if b > 127]
    assert offending == []


def test_the_open_questions_are_recorded_in_the_module_docstring():
    """The unresolved contract must be visible where the code is read."""
    doc = gate.__doc__ or ""
    assert "OPEN, ASKED OF SIBLING-C ON 2026-09-07" in doc


def test_the_measured_numbers_and_the_known_limits_are_recorded(tmp_path):
    """The docstring makes empirical claims, so it has to carry them.

    Two prose-falsity findings in this tree were docstrings describing a
    mechanism the code no longer had. A docstring that cites measurements must
    name them where the code is read.
    """
    doc = gate.__doc__ or ""
    assert "MEASURED 2026-09-07, ON 313 REAL TRANSCRIPTS" in doc
    assert "LIMITS - STATED, NOT HIDDEN" in doc
