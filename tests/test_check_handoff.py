"""Tests for `tools/check_handoff.py`, the hand-off content gate.

PORTED 2026-10-08 from `tests/test_publish_next_session.py` when MAIN's 2246
ORDER (FLEET-KIT v13, section 1) retired the Desktop shortcut. That module
converged a `.lnk` AND enforced every content rule on the hand-off; the
shortcut half is gone and the content half lives on here unchanged. Every arm
that drove `publish()` into a temp directory now drives `check_text()`, which
runs the same validation without a destination: there is no longer a write
whose absence could be asserted, so the claim each arm keeps is the refusal
itself.

THE RULES, each pinned below:

- A TRUNCATED hand-off is refused. A truncated hand-off and a complete one both
  read as current; only one is missing the context that makes it useful.
- NON-ASCII is refused, naming the codepoint.
- More than one fenced block is refused as ambiguous; a raw (fence-less) file
  is the whole hand-off.
- A CREDENTIAL or an ACCOUNT PATH is refused, and the refusal never echoes it.
  `RSC-NEXT-SESSION.txt` is tracked in a public repository and is pasted by
  hand into cold sessions.
- The SESSION counter (FLEET-COMMON item 13) must be one readable column-0
  `SESSION: <n>` line, or `/done` would write a guess plus one.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from tools import check_handoff as ch

REPO_ROOT = Path(__file__).resolve().parent.parent
FENCE = "`" * 3
TOOL = REPO_ROOT / "tools" / "check_handoff.py"


def _long_block(marker: str = "payload") -> str:
    """An ASCII block comfortably over the truncation floor."""
    line = f"{marker} line that exists only to clear the byte floor\n"
    return line * (1 + ch.MIN_BYTES // len(line))


def _source_with(block: str) -> str:
    return f"# Next session prompt\n\nPreamble.\n\n{FENCE}\n{block}{FENCE}\n\nTrailing prose.\n"


def _with_counter(text: str, n: int = 7) -> str:
    return text + f"SESSION: {n}\n"


def _block(payload: str) -> str:
    """A syntactically valid hand-off carrying `payload`, over the byte floor.

    The filler is deliberate: an undersized block is refused as
    `prompt_too_short` BEFORE the leak scan runs, so a probe that forgets it
    proves nothing about the leak scan.
    """
    filler = "\nfiller line that carries no secret and no account path."
    body = payload + filler * 90
    assert len(body.encode("ascii", "replace")) > ch.MIN_BYTES
    return f"{FENCE}\n{body}\n{FENCE}\n"


def _block_body(payload: str) -> str:
    """`payload` plus enough filler to clear the truncation floor."""
    filler = "filler line that carries no secret and no account path.\n"
    return payload + "\n" + filler * 90


# ---------------------------------------------------------------------------
# Extraction - fenced or raw, never ambiguous
# ---------------------------------------------------------------------------


def test_the_single_fenced_block_is_extracted_without_its_fences():
    block = _long_block()
    extracted = ch.extract_prompt(_source_with(block))
    assert extracted == block
    assert FENCE not in extracted


def test_a_fenceless_source_is_the_hand_off_in_its_entirety():
    block = _long_block()
    assert ch.extract_prompt(block) == block


def test_a_fenceless_source_is_still_held_to_every_other_guard():
    with pytest.raises(ch.Refusal) as caught:
        ch.extract_prompt("too short\n")
    assert caught.value.reason == "prompt_too_short"


def test_a_source_with_two_fenced_blocks_is_refused():
    block = _long_block()
    doubled = _source_with(block) + f"\n{FENCE}\nsecond block\n{FENCE}\n"
    with pytest.raises(ch.Refusal) as caught:
        ch.extract_prompt(doubled)
    assert caught.value.reason == "multiple_prompt_blocks"


def test_a_truncated_block_is_refused():
    with pytest.raises(ch.Refusal) as caught:
        ch.extract_prompt(_source_with("too short\n"))
    assert caught.value.reason == "prompt_too_short"


def test_the_size_floor_is_two_thousand_bytes():
    """The ROADMAP entry for the 2246 ORDER names this floor; it moved, unchanged."""
    assert ch.MIN_BYTES == 2000


def test_non_ascii_in_the_block_is_refused_and_names_the_codepoint():
    # Escaped, never literal: this file is held to the same ASCII rule it tests.
    block = _long_block() + "an em-dash \u2014 sneaks in\n"
    with pytest.raises(ch.Refusal) as caught:
        ch.extract_prompt(_source_with(block))
    assert caught.value.reason == "non_ascii"
    assert "U+2014" in caught.value.detail


# ---------------------------------------------------------------------------
# The SESSION counter - FLEET-COMMON item 13
# ---------------------------------------------------------------------------


def test_check_text_reports_the_bytes_and_the_counter():
    block = _long_block()
    report = ch.check_text(_with_counter(block, 64))
    assert report["ok"] is True
    assert report["session"] == 64
    assert report["bytes"] >= ch.MIN_BYTES


@pytest.mark.parametrize(
    "tail",
    [
        pytest.param("", id="missing"),
        pytest.param("SESSION: 5\nSESSION: 6\n", id="duplicate"),
        pytest.param("SESSION: five\n", id="garbled"),
        pytest.param("SESSION: 0\n", id="zero"),
    ],
)
def test_a_bad_session_counter_is_refused(tail):
    with pytest.raises(ch.Refusal) as caught:
        ch.check_text(_long_block() + tail)
    assert caught.value.reason == "session_counter"


def test_the_counter_check_runs_after_the_content_rules():
    """A short file is refused for its size first, whatever its counter says."""
    with pytest.raises(ch.Refusal) as caught:
        ch.check_text("too short\n")
    assert caught.value.reason == "prompt_too_short"


def test_the_counter_parser_is_the_session_hook_s_own():
    """One parser, not two that can disagree about what the counter is."""
    from tools import session_checklist

    assert ch.session_number is session_checklist.session_number


# ---------------------------------------------------------------------------
# Message hygiene - a refusal is printed and pasted around
# ---------------------------------------------------------------------------


def test_no_module_constant_names_a_user_directory_or_a_drive():
    for name, value in vars(ch).items():
        if not name.isupper() or not isinstance(value, str):
            continue
        assert "\\Users" not in value, f"{name} names a user directory"
        assert "/Users" not in value, f"{name} names a user directory"
        assert not any(
            f"{letter}:\\" in value or f"{letter}:/" in value for letter in "CDEF"
        ), f"{name} names a drive"


def test_every_module_constant_is_seven_bit_ascii():
    for name, value in vars(ch).items():
        if isinstance(value, str):
            assert value.isascii(), f"{name} is not 7-bit ASCII"


def test_no_refusal_names_a_path(tmp_path):
    emitted = []
    for bad_source in ("short raw source\n", _source_with("short\n"), _long_block()):
        with pytest.raises(ch.Refusal) as caught:
            ch.check_text(bad_source)
        emitted.append(caught.value.detail)

    # Spelled through `chr()` so this file does not itself carry the shape its
    # own sweeps refuse.
    account_line = "cache lives at C" + chr(58) + chr(92) + "Users" + chr(92) + "someone" + chr(92) + "AppData\n"
    with pytest.raises(ch.Refusal) as caught:
        ch.check_text(_with_counter(_source_with(account_line + _long_block())))
    assert caught.value.reason == "account_path"
    emitted.append(caught.value.detail)
    assert "someone" not in caught.value.detail, "the refusal echoed the account name"

    for text in emitted:
        assert str(tmp_path) not in text, f"a message named a full path: {text}"
        assert "\\Users" not in text and "/Users" not in text, text


# ---------------------------------------------------------------------------
# End to end against the tree's own hand-off
# ---------------------------------------------------------------------------


def _repo_hand_off() -> str:
    return (REPO_ROOT / "RSC-NEXT-SESSION.txt").read_text(encoding="utf-8")


def test_the_repo_hand_off_passes_the_gate():
    """If RSC-NEXT-SESSION.txt stops passing, this goes red HERE, not at /done."""
    source = _repo_hand_off()
    report = ch.check_text(source)
    assert report["bytes"] >= ch.MIN_BYTES
    assert ch.extract_prompt(source).isascii()


def test_the_repo_hand_off_block_carries_the_bootstrap_instruction():
    block = ch.extract_prompt(_repo_hand_off())
    assert "CLAUDE.md" in block
    assert "ROADMAP.md" in block


def test_the_repo_hand_off_names_this_gate_and_not_the_retired_one():
    """The /done gate list in the hand-off must run the tool that exists."""
    source = _repo_hand_off()
    assert "python tools/check_handoff.py" in source
    assert "publish_next_session" not in source


# ---------------------------------------------------------------------------
# Credentials and account paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ("export NIMBLE_API_KEY=abc123def456ghi789jkl012mno345pq", "secret_literal"),
        ('"ANTHROPIC_API_KEY": "sk-ant-api03-AAAAAAAAAAAAAAAAAAAA"', "secret_literal"),
        ("token sk-" + "B" * 32, "secret_literal"),
        ("gh token ghp_" + "C" * 36, "secret_literal"),
        (r"run C:\Users\someoperator\AppData\Local\Programs\Python", "account_path"),
        ("run /c/Users/someoperator/AppData/Local", "account_path"),
        ("run /mnt/c/Users/someoperator/.claude", "account_path"),
    ],
)
def test_a_leaking_block_is_refused(payload, reason):
    with pytest.raises(ch.Refusal) as caught:
        ch.extract_prompt(_block(payload))
    assert caught.value.reason == reason


def test_the_refusal_never_echoes_the_secret_it_caught():
    secret = "sk-" + "D" * 40
    with pytest.raises(ch.Refusal) as caught:
        ch.extract_prompt(_block(f"token {secret}"))
    rendered = str(caught.value)
    assert secret not in rendered, "the refusal message echoed the credential"
    assert "D" * 40 not in rendered


@pytest.mark.parametrize(
    "innocent",
    [
        "set NIMBLE_API_KEY in the machine environment before running",
        "NIMBLE_API_KEY=${NIMBLE_API_KEY}",
        "ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%",
        "path C:/Users/<account>/AppData/Local/Programs",
        "slots.py 629c3d511d2500f92d25fbe102a7a8c73644c027291f46b8796565a1e839f865",
        "commit e77ccd466e02b91887604c9875e694109a4c1ac4",
        # Built rather than written: see tests/test_machine_identity.py.
        "C:" + chr(92) + "Users" + chr(92) + "Public" + chr(92) + "Desktop",
        "python -m pytest tests",
    ],
)
def test_legitimate_handoff_content_survives(innocent):
    assert ch.extract_prompt(_block(innocent))


def test_the_leak_scan_is_not_vacuous():
    assert [r for r, _ in ch.scan_for_leaks("sk-" + "E" * 30)] == ["secret_literal"]
    assert [r for r, _ in ch.scan_for_leaks(r"C:\Users\someoperator\x")] == ["account_path"]
    assert ch.scan_for_leaks("nothing to see here") == []


# An environment reference is the destination of the rule, not a violation of
# it. Each exemption arm is ARMED FIRST by its literal twin.

_LITERAL_TWIN = '"0123456789abcdef0123456789abcdef"'


@pytest.mark.parametrize(
    ("reference", "twin"),
    [
        ("$env:GEMINI_API_KEY = $key", "$env:GEMINI_API_KEY = " + _LITERAL_TWIN),
        ("ANTHROPIC_API_KEY = $env:ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY = " + _LITERAL_TWIN),
        ("ANTHROPIC_API_KEY = $Env:ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY = " + _LITERAL_TWIN),
        (
            'RIOT_API_KEY = [Environment]::GetEnvironmentVariable("RIOT_API_KEY")',
            "RIOT_API_KEY = " + _LITERAL_TWIN,
        ),
        (
            'RIOT_API_KEY = [Environment]::getenvironmentvariable("RIOT_API_KEY")',
            "RIOT_API_KEY = " + _LITERAL_TWIN,
        ),
        # The casing only the `(?i:)` flag rescues.
        (
            'RIOT_API_KEY = [Environment]::GETENVIRONMENTVARIABLE("RIOT_API_KEY")',
            "RIOT_API_KEY = " + _LITERAL_TWIN,
        ),
    ],
)
def test_a_powershell_environment_reference_is_not_a_leak(reference, twin):
    assert ch.scan_for_leaks(twin), "the binding shape did not fire on the twin: " + twin
    assert ch.scan_for_leaks(reference) == [], "a lookup was refused: " + reference


@pytest.mark.parametrize(
    ("reference", "twin"),
    [
        ("NIMBLE_API_KEY=%NIMBLE_API_KEY2%", "NIMBLE_API_KEY=" + _LITERAL_TWIN),
        ("GEMINI_API_KEY=${gemini_api_key}", "GEMINI_API_KEY=" + _LITERAL_TWIN),
        ("ANTHROPIC_API_KEY=%COMMONPROGRAMW6432%", "ANTHROPIC_API_KEY=" + _LITERAL_TWIN),
        ("RIOT_API_KEY=%PROGRAMFILES(X86)%", "RIOT_API_KEY=" + _LITERAL_TWIN),
        ("NIMBLE_API_KEY=%CUDA_PATH_V13_3%", "NIMBLE_API_KEY=" + _LITERAL_TWIN),
    ],
)
def test_an_environment_name_outside_the_narrow_class_is_not_a_leak(reference, twin):
    assert ch.scan_for_leaks(twin), "the binding shape did not fire on the twin: " + twin
    assert ch.scan_for_leaks(reference) == [], "an env name was refused: " + reference


@pytest.mark.parametrize(
    "literal",
    [
        'NIMBLE_API_KEY = "0123456789abcdef0123456789abcdef"',
        'GEMINI_API_KEY = "abc$key"',
        'GEMINI_API_KEY=$key"abc123"',
        'NIMBLE_API_KEY = "%50-off-never-closed"',
        'RIOT_API_KEY = "${unterminated"',
        "ANTHROPIC_API_KEY = 0123456789abcdef",
    ],
)
def test_a_real_literal_is_still_refused_after_the_widening(literal):
    assert [reason for reason, _ in ch.scan_for_leaks(literal)] == ["secret_literal"], (
        "the widened exemption swallowed a real literal: " + literal
    )


def test_a_hand_off_that_binds_its_key_from_the_environment_passes():
    source = _with_counter(_source_with(_block_body("$env:GEMINI_API_KEY = $key")))
    assert ch.check_text(source)["ok"] is True
    assert "$env:GEMINI_API_KEY" in ch.extract_prompt(source)


# ---------------------------------------------------------------------------
# Vendor prefixes - the roster comes from the sweep module, not from the tool,
# so deleting a prefix from the tool's table turns these arms RED.
# ---------------------------------------------------------------------------

from tests.test_no_secret_literals import (  # noqa: E402
    ADVERSARY_PROBE,
    BOUNDARY_BREAK_TOKENS,
    OUT_OF_SCOPE_BINDINGS,
    PRECEDING_CLASS_PROBES,
    PRECEDING_PROBE_TOKEN,
    SEGMENTATION_LAYOUTS,
    SEPARATOR_DUMMY,
    SEPARATOR_EXEMPT,
    SEPARATOR_PROBES,
    SYNTHETIC_BODY,
    VENDOR_LAYOUT_PROBES,
    VENDOR_PREFIX_ROSTER,
)


@pytest.mark.parametrize("prefix", VENDOR_PREFIX_ROSTER)
def test_every_vendor_prefix_is_refused_by_the_gate(prefix):
    with pytest.raises(ch.Refusal) as caught:
        ch.check_text(_with_counter(_block("token " + prefix + SYNTHETIC_BODY)))
    assert caught.value.reason == "secret_literal", (
        "prefix " + prefix + " was not refused as a credential"
    )


def test_the_refusal_names_the_prefix_without_echoing_the_token():
    body = "9" * 40
    with pytest.raises(ch.Refusal) as caught:
        ch.extract_prompt(_block("slack xoxa-" + body))
    assert "xoxa-" in caught.value.detail
    assert body not in str(caught.value), "the refusal echoed the credential"


@pytest.mark.parametrize(
    "innocent",
    [
        "the task-argv-does-not-arm case",
        "the task-argv-is-a-dry-run case",
        "the task-name-argument-is-dropped case",
        "risk-weighted-resin-budget-notes",
        "slots.py 629c3d511d2500f92d25fbe102a7a8c73644c027291f46b8796565a1e839f865",
        "commit e77ccd466e02b91887604c9875e694109a4c1ac4",
        "python -m pytest tests",
    ],
)
def test_hyphen_segmented_prose_still_passes(innocent):
    assert ch.extract_prompt(_block(innocent))


@pytest.mark.parametrize(
    ("prefix", "layout", "token"),
    VENDOR_LAYOUT_PROBES,
    ids=[prefix + "/" + layout for prefix, layout, _ in VENDOR_LAYOUT_PROBES],
)
def test_no_vendor_layout_combination_is_accepted_by_the_gate(prefix, layout, token):
    with pytest.raises(ch.Refusal) as caught:
        ch.extract_prompt(_block("token " + token))
    assert caught.value.reason == "secret_literal", (
        prefix + " at layout " + layout + " was not refused as a credential"
    )


def test_the_probe_set_reaching_this_module_is_not_empty():
    """Derived, not spelled: prefixes times layouts, floored above zero."""
    expected = len(VENDOR_PREFIX_ROSTER) * len(SEGMENTATION_LAYOUTS)
    assert expected > 0, "the roster or the layout set reaching this module is empty"
    assert len(VENDOR_LAYOUT_PROBES) == expected


def test_the_adversary_probe_token_is_refused():
    with pytest.raises(ch.Refusal) as caught:
        ch.check_text(_with_counter(_block("slack " + ADVERSARY_PROBE)))
    assert caught.value.reason == "secret_literal"


def test_the_imported_boundary_probe_sets_are_not_empty():
    assert len(BOUNDARY_BREAK_TOKENS) == 3
    assert len(PRECEDING_CLASS_PROBES) == 15


@pytest.mark.parametrize(
    ("name", "text"),
    BOUNDARY_BREAK_TOKENS,
    ids=[name for name, _ in BOUNDARY_BREAK_TOKENS],
)
def test_no_break_set_token_passes_the_gate(name, text):
    with pytest.raises(ch.Refusal) as caught:
        ch.check_text(_with_counter(_block("note " + text)))
    assert caught.value.reason == "secret_literal", name + " was not refused"


@pytest.mark.parametrize(
    ("name", "preceding", "expected_caught"),
    PRECEDING_CLASS_PROBES,
    ids=[name for name, _, _ in PRECEDING_CLASS_PROBES],
)
def test_each_preceding_character_class_is_pinned_at_the_gate(name, preceding, expected_caught):
    """The `False` rows are the left boundary's PRICE, pinned so it stays visible."""
    source = _with_counter(_block("note " + preceding + PRECEDING_PROBE_TOKEN))
    if expected_caught:
        with pytest.raises(ch.Refusal) as caught:
            ch.check_text(source)
        assert caught.value.reason == "secret_literal"
    else:
        assert ch.check_text(source)["ok"], name + "-preceded text no longer passes"
        assert PRECEDING_PROBE_TOKEN in ch.extract_prompt(source), (
            "the arm claims this class is given up but the gate discarded it"
        )


#: The adversary's exact break line, SYNTHETIC: body is 24 repeated capital A,
#: preceded by an UNDERSCORE.
INJECTED_HAND_OFF_LINE = (
    "The Anthropic key was cached at ops/runtime/cache_"
    + "sk-ant-api03-"
    + "A" * 24
    + ".json - delete it."
)


def test_the_tree_s_own_hand_off_with_an_injected_token_is_refused():
    """A CONTROL runs first: the unmodified hand-off passes, so the refusal
    below is about the injection rather than about the file."""
    source = _repo_hand_off()
    assert ch.check_text(source)["ok"], "the tree's own hand-off fails; the arm below is mute"

    poisoned = INJECTED_HAND_OFF_LINE + "\n" + source
    assert poisoned.count(FENCE) == source.count(FENCE), "the injection moved a fence"
    assert INJECTED_HAND_OFF_LINE in poisoned

    with pytest.raises(ch.Refusal) as caught:
        ch.check_text(poisoned)
    assert caught.value.reason == "secret_literal"


def test_the_refusal_reports_the_match_span_as_an_upper_bound():
    body = "C" * 30
    payload = "ghp_" + body + "-secret_literal_notes"
    with pytest.raises(ch.Refusal) as caught:
        ch.extract_prompt(_block(payload))
    detail = caught.value.detail
    assert "match spans" in detail
    assert "UPPER BOUND" in detail
    assert body not in detail, "the refusal echoed the credential"
    assert str(len(payload)) in detail
    assert len(payload) > len("ghp_" + body)


def test_a_right_boundary_would_lose_detections_and_is_why_there_is_none():
    vendor = next(v for v in ch.VENDOR_TOKENS if v.prefix == "xoxb-")
    lost = "xoxb-" + "1" * 16 + "_tail"
    kept = "xoxb-" + "1" * 16 + ".json"
    assert ch.scan_for_leaks(lost) != [], "the probe is no longer caught at all"
    assert ch.scan_for_leaks(kept) != []
    with_right = re.compile(vendor.pattern() + r"(?![A-Za-z0-9_\-])")
    assert with_right.search(lost) is None, (
        "a right boundary no longer costs this detection; re-measure the trade"
    )
    assert with_right.search(kept) is not None


# ---------------------------------------------------------------------------
# The name-value separator
# ---------------------------------------------------------------------------


def test_the_imported_separator_probe_sets_are_not_empty():
    assert len(SEPARATOR_PROBES) == 16
    assert len(OUT_OF_SCOPE_BINDINGS) == 5
    assert len(SEPARATOR_EXEMPT) == 7
    assert set(SEPARATOR_DUMMY) == {"D"}, "the dummy body stopped being a dummy"


@pytest.mark.parametrize(
    ("name", "text"), SEPARATOR_PROBES, ids=[name for name, _ in SEPARATOR_PROBES]
)
def test_no_in_scope_separator_passes_the_gate(name, text):
    with pytest.raises(ch.Refusal) as caught:
        ch.check_text(_with_counter(_block("note " + text)))
    assert caught.value.reason == "secret_literal", name + " was not refused"


@pytest.mark.parametrize(
    ("name", "text"), SEPARATOR_EXEMPT, ids=[name for name, _ in SEPARATOR_EXEMPT]
)
def test_an_environment_lookup_still_passes_after_the_widening(name, text):
    source = _with_counter(_source_with(_block_body(text)))
    assert ch.check_text(source)["ok"] is True, "the widening refused a lookup: " + name
    assert text in ch.extract_prompt(source)


@pytest.mark.parametrize(
    ("name", "text"), OUT_OF_SCOPE_BINDINGS, ids=[name for name, _ in OUT_OF_SCOPE_BINDINGS]
)
def test_the_out_of_scope_shapes_still_pass_and_the_cost_is_pinned_here(name, text):
    """THE COST ARM: no-operator prose and off-roster names are NOT caught.
    Pinned at the reading measured, so closing either is a ruling, not a drift."""
    source = _with_counter(_source_with(_block_body(text)))
    assert ch.check_text(source)["ok"] is True, name + " changed reading without a ruling"
    assert SEPARATOR_DUMMY in ch.extract_prompt(source)


def test_the_repo_hand_off_still_passes_under_the_widened_separator():
    """Vacuous about the separator while no rostered name is in the hand-off;
    the count is asserted so the day one enters, the arm's meaning changes
    visibly."""
    block = ch.extract_prompt(_repo_hand_off())
    mentioned = {name: block.count(name) for name in ch.SECRET_NAMES}
    assert sum(mentioned.values()) == 0, repr({k: v for k, v in mentioned.items() if v})
    assert ch.scan_for_leaks(block) == []


def test_the_two_detectors_agree_on_every_separator_probe():
    from tests.test_no_secret_literals import scan_text

    rows = (
        [(n, t, True) for n, t in SEPARATOR_PROBES]
        + [(n, t, False) for n, t in OUT_OF_SCOPE_BINDINGS]
        + [(n, t, False) for n, t in SEPARATOR_EXEMPT]
    )
    assert len(rows) == 28
    disagreements = [
        name for name, text, _ in rows if bool(ch.scan_for_leaks(text)) != bool(scan_text(text))
    ]
    assert disagreements == [], "the gate and the sweep disagree at " + repr(disagreements)
    wrong = [name for name, text, expected in rows if bool(ch.scan_for_leaks(text)) is not expected]
    assert wrong == [], "a probe changed reading: " + repr(wrong)


# ---------------------------------------------------------------------------
# The command line - run the way /done runs it, from another directory
# ---------------------------------------------------------------------------


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        shell=False,
        check=False,
        timeout=120,
    )


def test_the_cli_passes_the_tree_s_own_hand_off_from_another_directory(tmp_path):
    """No in-process arm can see a `sys.path` bootstrap crash; this one can."""
    completed = _run_cli(cwd=tmp_path)
    assert "Traceback" not in completed.stderr, completed.stderr
    assert completed.returncode == 0, completed.stdout + completed.stderr
    lines = completed.stdout.splitlines()
    assert len(lines) == 1 and lines[0].startswith("check_handoff: ok"), completed.stdout


def test_the_cli_refuses_with_one_line_and_a_nonzero_exit(tmp_path):
    bad = tmp_path / "handoff.txt"
    bad.write_bytes(b"too short\nSESSION: 3\n")
    completed = _run_cli(str(bad), cwd=tmp_path)
    assert "Traceback" not in completed.stderr, completed.stderr
    assert completed.returncode != 0
    lines = completed.stdout.splitlines()
    assert len(lines) == 1, completed.stdout
    assert "prompt_too_short" in lines[0]
    assert str(tmp_path) not in completed.stdout, "the refusal named a full path"


def test_the_cli_refuses_a_bad_counter(tmp_path):
    bad = tmp_path / "handoff.txt"
    bad.write_bytes(_long_block().encode("ascii"))
    completed = _run_cli(str(bad), cwd=tmp_path)
    assert completed.returncode != 0
    assert "session_counter" in completed.stdout


def test_the_cli_reports_an_unreadable_file_without_a_traceback(tmp_path):
    completed = _run_cli(str(tmp_path / "absent.txt"), cwd=tmp_path)
    assert "Traceback" not in completed.stderr, completed.stderr
    assert completed.returncode != 0
    assert "unreadable" in completed.stdout
    assert str(tmp_path) not in completed.stdout


# ---------------------------------------------------------------------------
# The shortcut is GONE - MAIN 2246 ORDER section 1
# ---------------------------------------------------------------------------


_SHORTCUT_TOKENS = (".lnk", "WScript", "Desktop", "make_shortcut", "subprocess")


def _shortcut_tokens_in(text: str) -> list[str]:
    return [token for token in _SHORTCUT_TOKENS if token in text]


def test_the_gate_has_no_shortcut_code_path():
    """FLEET-COMMON item 5 dropped the Desktop shortcut. This gate reads one
    file and writes nothing; a `.lnk` or a Desktop reference coming back is a
    regression of the order, not a feature."""
    found = _shortcut_tokens_in(TOOL.read_text(encoding="utf-8"))
    assert found == [], "shortcut tokens reappeared in tools/check_handoff.py: " + repr(found)


def test_the_retired_shortcut_modules_are_gone():
    for rel in (
        "tools/publish_next_session.py",
        "scripts/make_shortcut.py",
        "tests/test_publish_next_session.py",
        "tests/test_make_shortcut.py",
    ):
        assert not (REPO_ROOT / rel).exists(), rel + " is back"


def test_the_shortcut_guard_is_not_vacuous():
    """Non-vacuity arm: the same scan fires on the retired writer's shape, and
    stays quiet on the gate's legitimate neighbour text."""
    planted = "LINK_NAME = 'X-NEXT-SESSION.lnk'\nshell = 'WScript.Shell'\n"
    assert _shortcut_tokens_in(planted) == [".lnk", "WScript"]
    assert _shortcut_tokens_in("SESSION: 64\nMIN_BYTES = 2000\n") == []
