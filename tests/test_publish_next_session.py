"""Tests for the Desktop backup copy of the next-session prompt.

THE INLINE FENCED BLOCK IS THE HAND-OFF. The Desktop file is a BACKUP of it,
which is the whole reason this module exists and the reason every arm below is
shaped the way it is: a backup that silently disagrees with the thing it backs
up is worse than no backup, because both read as current.

So the source of truth is `NEXT_SESSION_PROMPT.md` and the publisher NEVER
accepts prompt text as an argument. It reads the fenced block out of that file
or it refuses. There is no code path that can write a hand-retyped copy.

THREE ARMS ARE ABOUT SAFETY RATHER THAN BEHAVIOUR:

- **The Desktop is SHARED with five sibling projects.** `CS-`, `LL-`, `LW-`,
  `RC-` and `RM-` prefixed hand-offs live beside ours. The target basename is a
  module constant and no function takes a filename parameter, so a path bug
  cannot reach a neighbour's file. That is asserted against the signatures
  rather than against a remembered list of call sites.
- **No message may name a directory**, matching `test_make_shortcut.py`. The
  Desktop sits under the user profile, so its path CONTAINS THE WINDOWS ACCOUNT
  NAME. Reports carry the basename and a byte count, never a full path.
- **A truncated or non-ASCII block is REFUSED, not written.** This is the point
  where the text leaves the toolchain for Notepad, which is exactly where the
  7-bit-ASCII hard rule earns itself.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from tools import publish_next_session as pns

REPO_ROOT = Path(__file__).resolve().parent.parent
FENCE = "`" * 3

# Every sibling hand-off basename observed on the shared Desktop. Ours must not
# be any of them, and must not be confusable with one at a glance.
SIBLING_TARGETS = (
    "CS-NEXT-SESSION.txt",
    "LL-NEXT-SESSION.txt",
    "LW-NEXT-SESSION.txt",
    "RC-NEXT-SESSION.txt",
    "RM-NEXT-SESSION.txt",
)


def _long_block(marker: str = "payload") -> str:
    """An ASCII block comfortably over the truncation floor."""
    line = f"{marker} line that exists only to clear the byte floor\n"
    return line * (1 + pns.MIN_BYTES // len(line))


def _source_with(block: str) -> str:
    return f"# Next session prompt\n\nPreamble.\n\n{FENCE}\n{block}{FENCE}\n\nTrailing prose.\n"


# ---------------------------------------------------------------------------
# Extraction - the source of truth is the file, never an argument
# ---------------------------------------------------------------------------


def test_the_single_fenced_block_is_extracted_without_its_fences():
    block = _long_block()
    extracted = pns.extract_prompt(_source_with(block))
    assert extracted == block
    assert FENCE not in extracted


def test_a_source_with_no_fenced_block_is_refused():
    with pytest.raises(pns.Refusal) as caught:
        pns.extract_prompt("# Next session prompt\n\nNo block here at all.\n")
    assert caught.value.reason == "no_prompt_block"


def test_a_source_with_two_fenced_blocks_is_refused():
    """Ambiguity is a refusal, not a guess at which block was meant."""
    block = _long_block()
    doubled = _source_with(block) + f"\n{FENCE}\nsecond block\n{FENCE}\n"
    with pytest.raises(pns.Refusal) as caught:
        pns.extract_prompt(doubled)
    assert caught.value.reason == "multiple_prompt_blocks"


def test_a_truncated_block_is_refused():
    """A truncated hand-off and a complete one both read as current."""
    with pytest.raises(pns.Refusal) as caught:
        pns.extract_prompt(_source_with("too short\n"))
    assert caught.value.reason == "prompt_too_short"


def test_non_ascii_in_the_block_is_refused_and_names_the_codepoint():
    # Escaped, never literal: this file is held to the same ASCII rule it tests.
    block = _long_block() + "an em-dash \u2014 sneaks in\n"
    with pytest.raises(pns.Refusal) as caught:
        pns.extract_prompt(_source_with(block))
    assert caught.value.reason == "non_ascii"
    assert "U+2014" in caught.value.detail


# ---------------------------------------------------------------------------
# Publishing - atomic, verified by read-back
# ---------------------------------------------------------------------------


def test_publish_writes_the_block_verbatim_and_reads_it_back(tmp_path):
    block = _long_block()
    report = pns.publish(_source_with(block), tmp_path)
    written = (tmp_path / pns.TARGET_NAME).read_text(encoding="ascii")
    assert written == block
    assert report["ok"] is True
    assert report["bytes"] == len(block.encode("ascii"))


def test_publish_writes_lf_endings_only(tmp_path):
    """The operator pastes this into a cold session; stray CR is noise."""
    pns.publish(_source_with(_long_block()), tmp_path)
    assert b"\r" not in (tmp_path / pns.TARGET_NAME).read_bytes()


def test_publish_leaves_no_temp_file_behind(tmp_path):
    pns.publish(_source_with(_long_block()), tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == [pns.TARGET_NAME]


def test_a_refused_publish_writes_nothing_at_all(tmp_path):
    with pytest.raises(pns.Refusal):
        pns.publish(_source_with("too short\n"), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_publishing_twice_overwrites_rather_than_accumulating(tmp_path):
    pns.publish(_source_with(_long_block("first")), tmp_path)
    pns.publish(_source_with(_long_block("second")), tmp_path)
    written = (tmp_path / pns.TARGET_NAME).read_text(encoding="ascii")
    assert "first" not in written
    assert "second" in written
    assert [p.name for p in tmp_path.iterdir()] == [pns.TARGET_NAME]


def test_a_missing_desktop_is_refused(tmp_path):
    with pytest.raises(pns.Refusal) as caught:
        pns.publish(_source_with(_long_block()), tmp_path / "nope")
    assert caught.value.reason == "no_desktop"


# ---------------------------------------------------------------------------
# Drift reporting - --check writes nothing
# ---------------------------------------------------------------------------


def test_check_reports_absent_when_nothing_has_been_published(tmp_path):
    report = pns.check(_source_with(_long_block()), tmp_path)
    assert report["present"] is False
    assert report["in_sync"] is False
    assert list(tmp_path.iterdir()) == []


def test_check_reports_in_sync_after_a_publish(tmp_path):
    source = _source_with(_long_block())
    pns.publish(source, tmp_path)
    assert pns.check(source, tmp_path)["in_sync"] is True


def test_check_reports_drift_when_the_source_moved_on(tmp_path):
    pns.publish(_source_with(_long_block("old")), tmp_path)
    report = pns.check(_source_with(_long_block("new")), tmp_path)
    assert report["present"] is True
    assert report["in_sync"] is False


# ---------------------------------------------------------------------------
# The shared Desktop - a path bug must not be able to reach a neighbour
# ---------------------------------------------------------------------------


def test_the_target_basename_is_a_constant_no_function_accepts(tmp_path):
    """No filename parameter anywhere, so no argument can redirect the write."""
    for name in ("publish", "check", "target_path"):
        parameters = set(inspect.signature(getattr(pns, name)).parameters)
        assert not parameters & {"name", "filename", "target", "target_name", "basename"}


def test_the_target_does_not_collide_with_a_sibling_project(tmp_path):
    assert pns.TARGET_NAME not in SIBLING_TARGETS
    assert pns.target_path(tmp_path).name == pns.TARGET_NAME


def test_the_temp_file_prefix_is_ours_and_hidden():
    """A crashed run must leave litter that is identifiably this project's."""
    assert pns.TEMP_PREFIX.startswith(".")
    assert "rsc" in pns.TEMP_PREFIX.lower()


# ---------------------------------------------------------------------------
# Message hygiene - the Desktop path carries the Windows account name
# ---------------------------------------------------------------------------


def test_no_module_constant_names_a_user_directory_or_a_drive():
    for name, value in vars(pns).items():
        if not name.isupper() or not isinstance(value, str):
            continue
        assert "\\Users" not in value, f"{name} names a user directory"
        assert "/Users" not in value, f"{name} names a user directory"
        assert not any(
            f"{letter}:\\" in value or f"{letter}:/" in value for letter in "CDEF"
        ), f"{name} names a drive"


def test_every_module_constant_is_seven_bit_ascii():
    for name, value in vars(pns).items():
        if isinstance(value, str):
            assert value.isascii(), f"{name} is not 7-bit ASCII"


def test_no_report_or_refusal_names_a_path(tmp_path):
    """Reports carry the basename and a byte count. Never a full path."""
    emitted = []

    source = _source_with(_long_block())
    emitted.extend(str(v) for v in pns.publish(source, tmp_path).values())
    emitted.extend(str(v) for v in pns.check(source, tmp_path).values())

    for bad_source, _reason in (
        ("no block here\n", "no_prompt_block"),
        (_source_with("short\n"), "prompt_too_short"),
    ):
        with pytest.raises(pns.Refusal) as caught:
            pns.publish(bad_source, tmp_path)
        emitted.append(caught.value.detail)

    with pytest.raises(pns.Refusal) as caught:
        pns.publish(source, tmp_path / "absent")
    emitted.append(caught.value.detail)

    for text in emitted:
        assert str(tmp_path) not in text, f"a message named a full path: {text}"
        assert "\\Users" not in text and "/Users" not in text, text


# ---------------------------------------------------------------------------
# End to end against the tree's own hand-off - the arm that catches real drift
# ---------------------------------------------------------------------------


def test_the_repo_hand_off_actually_publishes(tmp_path):
    """If NEXT_SESSION_PROMPT.md stops being publishable, this goes red HERE.

    Every other arm runs against a synthetic source. This one runs against the
    file the ritual actually reads, so a prose edit that adds a second fence or
    slips in a smart quote fails a test rather than failing at session end.
    """
    source = (REPO_ROOT / "NEXT_SESSION_PROMPT.md").read_text(encoding="utf-8")
    report = pns.publish(source, tmp_path)
    assert report["bytes"] >= pns.MIN_BYTES
    assert (tmp_path / pns.TARGET_NAME).read_text(encoding="ascii").isascii()


def test_the_repo_hand_off_block_carries_the_bootstrap_instruction():
    """A hand-off that does not tell a cold session what to read is not one."""
    source = (REPO_ROOT / "NEXT_SESSION_PROMPT.md").read_text(encoding="utf-8")
    block = pns.extract_prompt(source)
    assert "CLAUDE.md" in block
    assert "ROADMAP.md" in block


# ---------------------------------------------------------------------------
# The hand-off is a PUBLICATION surface - credentials and account paths
# ---------------------------------------------------------------------------
#
# Added 2026-09-07 after Sibling-E asked whether anyone gated the
# hand-off more widely than ASCII and truncation. This tree's honest answer was
# no, and it was measured rather than assumed: a block carrying a live-shaped
# NIMBLE_API_KEY and one carrying an absolute path naming the operator's
# account were each published clean to the Desktop.
#
# Why this gate and not the tracked-tree sweeps. `tests/test_machine_identity.py`
# and `tests/test_no_secret_literals.py` both run over the COMMITTED tree.
# Neither sees a block on its way OUT to the Desktop, and that is the one path
# that leaves the toolchain - pasted by hand into cold sessions and quoted into
# notes to four sibling repos, from a repository that is public.


def _block(payload: str) -> str:
    """A syntactically valid hand-off carrying `payload`, over the byte floor.

    The filler is deliberate: an undersized block is refused as `prompt_too_short`
    BEFORE the leak scan runs, so a probe that forgets it proves nothing about
    the leak scan. Measured that failure once while writing these arms.
    """
    from tools.publish_next_session import FENCE, MIN_BYTES

    filler = "\nfiller line that carries no secret and no account path."
    body = payload + filler * 90
    assert len(body.encode("ascii", "replace")) > MIN_BYTES
    return f"{FENCE}\n{body}\n{FENCE}\n"


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
    from tools.publish_next_session import Refusal, extract_prompt

    with pytest.raises(Refusal) as caught:
        extract_prompt(_block(payload))
    assert caught.value.reason == reason


def test_the_refusal_never_echoes_the_secret_it_caught():
    """A refusal is printed and pasted around. Quoting the key would publish it."""
    from tools.publish_next_session import Refusal, extract_prompt

    secret = "sk-" + "D" * 40
    with pytest.raises(Refusal) as caught:
        extract_prompt(_block(f"token {secret}"))
    rendered = str(caught.value)
    assert secret not in rendered, "the refusal message echoed the credential"
    assert "D" * 40 not in rendered


@pytest.mark.parametrize(
    "innocent",
    [
        # The partner guard. A gate that refused these would be turned off.
        "set NIMBLE_API_KEY in the machine environment before running",
        "NIMBLE_API_KEY=${NIMBLE_API_KEY}",
        "ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%",
        "path C:/Users/<account>/AppData/Local/Programs",
        "slots.py 629c3d511d2500f92d25fbe102a7a8c73644c027291f46b8796565a1e839f865",
        "commit e77ccd466e02b91887604c9875e694109a4c1ac4",
        # Built rather than written: the Windows shared profile is a real
        # account-shaped path, and spelling it literally here would make
        # this file trip tests/test_machine_identity.py. The gate must still
        # let it through - refusing a path that identifies nobody is the
        # false positive that gets a gate switched off.
        "C:" + chr(92) + "Users" + chr(92) + "Public" + chr(92) + "Desktop",
        "python -m pytest tests",
    ],
)
def test_legitimate_handoff_content_survives(innocent):
    from tools.publish_next_session import extract_prompt

    assert extract_prompt(_block(innocent))


def test_the_leak_scan_is_not_vacuous():
    """Both detector halves fire, so neither is dead code carrying a comment."""
    from tools.publish_next_session import scan_for_leaks

    assert [r for r, _ in scan_for_leaks("sk-" + "E" * 30)] == ["secret_literal"]
    assert [r for r, _ in scan_for_leaks(r"C:\Users\someoperator\x")] == ["account_path"]
    assert scan_for_leaks("nothing to see here") == []


# ---------------------------------------------------------------------------
# AN ENVIRONMENT REFERENCE IS THE DESTINATION OF THE RULE, NOT A VIOLATION OF IT
# ---------------------------------------------------------------------------
#
# THE DEFECT, measured in-process against the real `scan_for_leaks` before these
# arms existed. Each of these is the CORRECT pattern and each was REFUSED:
#
#     "$env:GEMINI_API_KEY = $key"                        -> secret_literal
#     "ANTHROPIC_API_KEY = $env:ANTHROPIC_API_KEY"        -> secret_literal
#     'RIOT_API_KEY = [Environment]::GetEnvironmentVariable("RIOT_API_KEY")'
#                                                         -> secret_literal
#     "NIMBLE_API_KEY=%NIMBLE_API_KEY2%"                  -> secret_literal
#     "GEMINI_API_KEY=${gemini_api_key}"                  -> secret_literal
#
# This is not a cosmetic false positive. `scan_for_leaks` is reached from
# `extract_prompt`, which every publish and every --check runs through, so a
# hand-off that told the next session to bind its key from the environment
# could not be published at all. A gate that refuses its own destination is a
# gate somebody switches off.
#
# TWO ROOT CAUSES, GRADED SEPARATELY BECAUSE THEY ARE DIFFERENT CHANGES.
#
#   DIALECT. `$env:NAME` is THE PowerShell spelling of an environment read, and
#   Windows resolves variable names case-insensitively - `$env:`, `$Env:` and
#   `$ENV:` are one variable. The exemption was written in Python `re`'s default
#   dialect, which is case-SENSITIVE, so it agreed with the machine on exactly
#   one of the three spellings and called the other two literals.
#
#   CLASS. `[A-Z_]+` over a population that also carries digits, lowercase and
#   punctuation. DERIVED BY SUBTRACTION FROM A REAL CORPUS rather than by
#   enumerating cases: of the 101 variable names in this process's own
#   environment block, measured on this box 2026-09-11, 93 match `[A-Z_]+` end
#   to end and EIGHT do not - PROGRAMW6432, PROGRAMFILES(X86),
#   COMMONPROGRAMFILES(X86), COMMONPROGRAMW6432, CUDA_PATH_V13_3, PYTHONUTF8,
#   ASL.LOG and SENTRY-TRACE. Those eight ARE the population the class could not
#   see: digits, parentheses, a dot and a hyphen, in a real environment block
#   rather than in a list somebody thought of.
#
# EVERY ARM BELOW FEEDS AN INPUT. None asserts that a pattern has a particular
# spelling - a shape arm pins format rather than behaviour and stays green
# against a matcher that has stopped matching anything at all. Each exemption
# arm is ARMED FIRST by its literal twin: the same binding with a real literal
# on the right-hand side must still be caught, which proves the binding shape
# fires on that text and that the empty result means "exempted" rather than
# "never looked at".

_LITERAL_TWIN = '"0123456789abcdef0123456789abcdef"'


@pytest.mark.parametrize(
    ("reference", "twin"),
    [
        # DIALECT - the PowerShell environment spellings, all three casings.
        ("$env:GEMINI_API_KEY = $key", "$env:GEMINI_API_KEY = " + _LITERAL_TWIN),
        (
            "ANTHROPIC_API_KEY = $env:ANTHROPIC_API_KEY",
            "ANTHROPIC_API_KEY = " + _LITERAL_TWIN,
        ),
        (
            "ANTHROPIC_API_KEY = $Env:ANTHROPIC_API_KEY",
            "ANTHROPIC_API_KEY = " + _LITERAL_TWIN,
        ),
        (
            'RIOT_API_KEY = [Environment]::GetEnvironmentVariable("RIOT_API_KEY")',
            "RIOT_API_KEY = " + _LITERAL_TWIN,
        ),
        (
            'RIOT_API_KEY = [Environment]::getenvironmentvariable("RIOT_API_KEY")',
            "RIOT_API_KEY = " + _LITERAL_TWIN,
        ),
        # THE CASING NOTHING ELSE RESCUES, and the reason the `(?i:)` on that
        # method name is load-bearing rather than decorative. The canonical
        # spelling is matched by the literal and the all-lowercase one by the
        # `getenv` alternative; SHOUTED, it is matched by neither, so this input
        # is the only one in the file that grades the flag. A mutation pass
        # unfolded that name while this arm was absent and NOTHING went red.
        (
            'RIOT_API_KEY = [Environment]::GETENVIRONMENTVARIABLE("RIOT_API_KEY")',
            "RIOT_API_KEY = " + _LITERAL_TWIN,
        ),
    ],
)
def test_a_powershell_environment_reference_is_not_a_leak(reference, twin):
    """The DIALECT half. PowerShell and Windows both resolve these case-blind."""
    from tools.publish_next_session import scan_for_leaks

    assert scan_for_leaks(twin), (
        "the binding shape did not fire on the literal twin, so an empty result "
        "for the reference below would prove nothing: " + twin
    )
    assert scan_for_leaks(reference) == [], (
        "an environment reference is the destination of this rule, not a "
        "violation of it, and refusing it blocks the publish path: " + reference
    )


@pytest.mark.parametrize(
    ("reference", "twin"),
    [
        # CLASS - the bound value is an environment reference whose NAME carries
        # a character outside [A-Z_]. The pairing of name to variable is
        # synthetic; what is under test is the shape of the VALUE.
        ("NIMBLE_API_KEY=%NIMBLE_API_KEY2%", "NIMBLE_API_KEY=" + _LITERAL_TWIN),
        ("GEMINI_API_KEY=${gemini_api_key}", "GEMINI_API_KEY=" + _LITERAL_TWIN),
        (
            "ANTHROPIC_API_KEY=%COMMONPROGRAMW6432%",
            "ANTHROPIC_API_KEY=" + _LITERAL_TWIN,
        ),
        ("RIOT_API_KEY=%PROGRAMFILES(X86)%", "RIOT_API_KEY=" + _LITERAL_TWIN),
        ("NIMBLE_API_KEY=%CUDA_PATH_V13_3%", "NIMBLE_API_KEY=" + _LITERAL_TWIN),
    ],
)
def test_an_environment_name_outside_the_narrow_class_is_not_a_leak(reference, twin):
    """The CLASS half. Five of the eight measured names live outside [A-Z_]+."""
    from tools.publish_next_session import scan_for_leaks

    assert scan_for_leaks(twin), (
        "the binding shape did not fire on the literal twin, so an empty result "
        "for the reference below would prove nothing: " + twin
    )
    assert scan_for_leaks(reference) == [], (
        "an environment variable name may carry digits, lowercase and "
        "punctuation; refusing one is an over-fire: " + reference
    )


@pytest.mark.parametrize(
    "literal",
    [
        # THE PARTNER GUARD. A sweep that scores 100 percent by exempting its
        # neighbours has failed, and every widening above is a chance to do
        # exactly that. These must all still be refused.
        'NIMBLE_API_KEY = "0123456789abcdef0123456789abcdef"',
        'GEMINI_API_KEY = "abc$key"',
        'GEMINI_API_KEY=$key"abc123"',
        'NIMBLE_API_KEY = "%50-off-never-closed"',
        'RIOT_API_KEY = "${unterminated"',
        "ANTHROPIC_API_KEY = 0123456789abcdef",
    ],
)
def test_a_real_literal_is_still_refused_after_the_widening(literal):
    from tools.publish_next_session import scan_for_leaks

    assert [reason for reason, _ in scan_for_leaks(literal)] == ["secret_literal"], (
        "the widened exemption swallowed a real literal: " + literal
    )


def test_a_hand_off_that_binds_its_key_from_the_environment_publishes(tmp_path):
    """The end-to-end arm: this is the path the over-fire actually blocked.

    Every other arm here drives `scan_for_leaks` directly. This one goes through
    `extract_prompt`, which is what `publish` and `--check` both call, so it
    fails at the publish boundary rather than at the predicate.
    """
    from tools.publish_next_session import publish

    report = publish(_source_with(_block_body("$env:GEMINI_API_KEY = $key")), tmp_path)
    assert report["ok"] is True
    written = (tmp_path / pns.TARGET_NAME).read_text(encoding="ascii")
    assert "$env:GEMINI_API_KEY" in written


def _block_body(payload: str) -> str:
    """`payload` plus enough filler to clear the truncation floor."""
    filler = "filler line that carries no secret and no account path.\n"
    return payload + "\n" + filler * 90


# ---------------------------------------------------------------------------
# NO VENDOR PREFIX REACHES THE DESKTOP - the gate that leaves the toolchain
# ---------------------------------------------------------------------------
#
# THE DEFECT, measured end to end 2026-09-11 through the real publish path with
# NO mutation, every arm in the tree green. The publisher's `SECRET_PREFIXES`
# and the sweep's `VENDOR_TOKEN` were left as two copies and labelled a known
# remaining pair. They had already drifted, and three Slack spellings leaked:
#
#     xoxb- + 24  ->  REFUSED    reason=secret_literal
#     xoxa- + 24  ->  PUBLISHED  ok=True, bytes=4718, token on disk
#     xoxs- + 24  ->  PUBLISHED  ok=True, bytes=4718, token on disk
#
# `tests/test_no_secret_literals.py` caught all three. It sweeps the COMMITTED
# tree. This module's gate is the only one on the path that LEAVES the
# toolchain, so a token the sweep catches and the publisher misses lands on the
# Desktop and gets pasted into a cold session.
#
# THE ROSTER IS IMPORTED FROM THE SWEEP MODULE, not from the tool. It is
# hand-written there, deliberately outside the single source, so that deleting a
# prefix from the tool's table turns these arms RED. An arm parametrized over
# the tool's own table would be checking the list against itself.

from tests.test_no_secret_literals import (  # noqa: E402
    SYNTHETIC_BODY,
    VENDOR_PREFIX_ROSTER,
)


@pytest.mark.parametrize("prefix", VENDOR_PREFIX_ROSTER)
def test_every_vendor_prefix_is_refused_by_the_publish_gate(prefix):
    """Each prefix driven as INPUT through `extract_prompt`, which every publish
    and every `--check` runs through. Not an assertion about a pattern spelling.
    """
    from tools.publish_next_session import Refusal, extract_prompt

    with pytest.raises(Refusal) as caught:
        extract_prompt(_block("token " + prefix + SYNTHETIC_BODY))
    assert caught.value.reason == "secret_literal", (
        "prefix " + prefix + " was not refused as a credential"
    )


@pytest.mark.parametrize("prefix", VENDOR_PREFIX_ROSTER)
def test_no_vendor_prefix_survives_a_real_publish(prefix, tmp_path):
    """The whole path, into a real directory: refused, and nothing written.

    `publish` is what writes bytes outside the repository, so this arm ends
    where the leak ended - at a file on disk. `tmp_path` stands in for the
    Desktop; the module's own `--desktop` override is what makes that possible
    without pointing the real ritual at a test directory.
    """
    with pytest.raises(pns.Refusal) as caught:
        pns.publish(_block("token " + prefix + SYNTHETIC_BODY), tmp_path)
    assert caught.value.reason == "secret_literal"
    assert list(tmp_path.iterdir()) == [], (
        "a refused publish left a file behind for prefix " + prefix
    )


def test_the_refusal_names_the_prefix_without_echoing_the_token():
    """The detail still names which vendor fired, and still quotes no secret."""
    from tools.publish_next_session import Refusal, extract_prompt

    body = "9" * 40
    with pytest.raises(Refusal) as caught:
        extract_prompt(_block("slack xoxa-" + body))
    assert "xoxa-" in caught.value.detail
    assert body not in str(caught.value), "the refusal echoed the credential"


@pytest.mark.parametrize(
    "innocent",
    [
        # NON-VACUITY, and the second half of the DEFECT. These were all
        # accepted by the SWEEP before the unification and must still be, and
        # the first three were REFUSED by the publisher - `sk-` is the tail of
        # `task-`, and the old shared 16-character floor over a class that
        # included the hyphen fired on hyphen-segmented English. Measured at
        # NINE hits across two tracked files at HEAD, out of 221 readable
        # tracked files, and re-derived this run. The unified rule separates
        # them by a LEFT BOUNDARY - in all nine, `sk-` is the tail of `task-`,
        # so the match does not start where a token starts. An UNBROKEN-RUN
        # rule was tried first and is what the section at the foot of this
        # module records as the regression it caused.
        "the task-argv-does-not-arm case",
        "the task-argv-is-a-dry-run case",
        "the task-name-argument-is-dropped case",
        "risk-weighted-resin-budget-notes",
        "slots.py 629c3d511d2500f92d25fbe102a7a8c73644c027291f46b8796565a1e839f865",
        "commit e77ccd466e02b91887604c9875e694109a4c1ac4",
        "python -m pytest tests",
    ],
)
def test_hyphen_segmented_prose_still_publishes(innocent):
    from tools.publish_next_session import extract_prompt

    assert extract_prompt(_block(innocent))


# ---------------------------------------------------------------------------
# A SEGMENTED CREDENTIAL MUST NOT REACH THE DESKTOP EITHER
# ---------------------------------------------------------------------------
#
# THE DEFECT THIS SECTION CLOSES, measured 2026-09-11 through the real publish
# path into a scratchpad directory, against bytes that were green everywhere:
#
#     xoxb- + 13 ones + "-" + 13 twos + "-" + 24 capitals   (SYNTHETIC)
#       scan_for_leaks -> []
#       publish()      -> ok True, bytes 5021, TOKEN ON DISK
#
# The arms above drive each prefix with a FLAT 40-character body, so the whole
# section was blind to segmentation: every prefix passed while every one of them
# leaked the moment the body carried the vendor's own separators. The probe set
# imported below is the cartesian product of prefix and layout, which is the
# axis a flat-body set cannot see.
#
# The roster still comes from the sweep module rather than the tool, for the
# reason given above: an arm parametrized over the tool's own table checks the
# list against itself.

from tests.test_no_secret_literals import (  # noqa: E402
    ADVERSARY_PROBE,
    VENDOR_LAYOUT_PROBES,
)


@pytest.mark.parametrize(
    ("prefix", "layout", "token"),
    VENDOR_LAYOUT_PROBES,
    ids=[prefix + "/" + layout for prefix, layout, _ in VENDOR_LAYOUT_PROBES],
)
def test_no_vendor_layout_combination_is_accepted_by_the_publish_gate(prefix, layout, token):
    from tools.publish_next_session import Refusal, extract_prompt

    with pytest.raises(Refusal) as caught:
        extract_prompt(_block("token " + token))
    assert caught.value.reason == "secret_literal", (
        prefix + " at layout " + layout + " was not refused as a credential"
    )


def test_the_probe_set_reaching_this_module_is_not_empty():
    """The floor. An emptied import parametrizes to nothing and skips at rc 0."""
    assert len(VENDOR_LAYOUT_PROBES) == 44


def test_the_adversary_probe_token_never_reaches_disk(tmp_path):
    """The end of the leak, measured where the leak ended - a file on disk.

    `tmp_path` stands in for the Desktop. The real ritual is never pointed at a
    test directory; `publish` takes the target as an argument for exactly this.
    """
    with pytest.raises(pns.Refusal) as caught:
        pns.publish(_block("slack " + ADVERSARY_PROBE), tmp_path)
    assert caught.value.reason == "secret_literal"
    assert list(tmp_path.iterdir()) == [], "a refused publish left a file behind"


# ---------------------------------------------------------------------------
# THE SUBJECT IS A HAND-OFF BLOCK, NOT THE TRACKED CORPUS
# ---------------------------------------------------------------------------
#
# Every rule in this detector's lineage was validated over tracked files. This
# module gates something else entirely: a block of PROSE, PATHS, shell commands
# and fenced code written by an agent, on its way out of the toolchain. The
# arms below drive the tree's OWN fenced hand-off - the real
# `NEXT_SESSION_PROMPT.md` block, not a synthetic stand-in - through the real
# `publish()`, into `tmp_path`. The module's `--desktop` override is what makes
# that possible without pointing the ritual at a test directory; the real
# Desktop is never a target here.

from tests.test_no_secret_literals import (  # noqa: E402
    BOUNDARY_BREAK_TOKENS,
    PRECEDING_CLASS_PROBES,
    PRECEDING_PROBE_TOKEN,
)


def test_the_imported_boundary_probe_sets_are_not_empty():
    """The floor. An emptied import parametrizes to nothing and skips at rc 0."""
    assert len(BOUNDARY_BREAK_TOKENS) == 3
    assert len(PRECEDING_CLASS_PROBES) == 15


@pytest.mark.parametrize(
    ("name", "text"),
    BOUNDARY_BREAK_TOKENS,
    ids=[name for name, _ in BOUNDARY_BREAK_TOKENS],
)
def test_no_break_set_token_survives_a_real_publish(name, text, tmp_path):
    """The end of the leak, measured where the leak ended - a file on disk.

    All three of these were PUBLISHED under the `(?<![A-Za-z0-9_])` boundary,
    and all three were refused by `git show HEAD:tools/publish_next_session.py`,
    which carried no boundary at all. Bodies are repeated characters.
    """
    with pytest.raises(pns.Refusal) as caught:
        pns.publish(_block("note " + text), tmp_path)
    assert caught.value.reason == "secret_literal", name + " was not refused"
    assert list(tmp_path.iterdir()) == [], "a refused publish left a file behind"


@pytest.mark.parametrize(
    ("name", "preceding", "expected_caught"),
    PRECEDING_CLASS_PROBES,
    ids=[name for name, _, _ in PRECEDING_CLASS_PROBES],
)
def test_each_preceding_character_class_is_pinned_at_the_publish_gate(
    name, preceding, expected_caught, tmp_path
):
    """THE COST ARM at the gate that actually writes bytes.

    The `False` rows are the boundary's PRICE, and they publish. That is not a
    hole left open by accident: a letter-preceded match is what the nine
    hyphen-segmented English false positives all were, and refusing them is
    what makes an operator switch a gate off. The price is pinned here so the
    next reader sees the trade instead of rediscovering it.
    """
    source = _block("note " + preceding + PRECEDING_PROBE_TOKEN)
    if expected_caught:
        with pytest.raises(pns.Refusal) as caught:
            pns.publish(source, tmp_path)
        assert caught.value.reason == "secret_literal"
        assert list(tmp_path.iterdir()) == [], "a refused publish left a file behind"
    else:
        report = pns.publish(source, tmp_path)
        assert report["ok"], name + "-preceded text no longer publishes"
        assert PRECEDING_PROBE_TOKEN in (tmp_path / pns.TARGET_NAME).read_text(
            encoding="ascii"
        ), "the arm claims this class is given up but nothing reached disk"


#: The adversary's exact break line, verbatim, SYNTHETIC: the body is 24
#: repeated capital A. Its preceding character is an UNDERSCORE, which is the
#: whole of why the `(?<![A-Za-z0-9_])` boundary let it through.
INJECTED_HAND_OFF_LINE = (
    "The Anthropic key was cached at ops/runtime/cache_"
    + "sk-ant-api03-"
    + "A" * 24
    + ".json - delete it."
)


def test_the_tree_s_own_hand_off_block_with_an_injected_token_never_reaches_disk(tmp_path):
    """REQUIREMENT 3. The real block, the real publish path, a temp directory.

    A CONTROL runs first: the unmodified block publishes clean into its own
    directory. Without that, a refusal below would be consistent with the block
    having been unpublishable all along, and the arm would prove nothing.

    The injection goes immediately after the opening fence, so the source still
    carries exactly two fence lines and `extract_prompt` reaches the leak scan
    rather than refusing for ambiguity first.
    """
    source = (REPO_ROOT / "NEXT_SESSION_PROMPT.md").read_text(encoding="utf-8")

    clean = tmp_path / "clean"
    clean.mkdir()
    control = pns.publish(source, clean)
    assert control["ok"], "the tree's own hand-off does not publish; the arm below is mute"
    assert (clean / pns.TARGET_NAME).is_file()

    lines = source.splitlines(keepends=True)
    opening = next(i for i, line in enumerate(lines) if line.rstrip("\r\n") == FENCE)
    poisoned = "".join(
        lines[: opening + 1] + [INJECTED_HAND_OFF_LINE + "\n"] + lines[opening + 1 :]
    )
    assert poisoned.count(FENCE) == source.count(FENCE), "the injection moved a fence"

    # ARMING: the line has to land INSIDE the block. A poisoned source whose
    # token sat in the surrounding prose would be refused by nothing and would
    # still read as a passing arm.
    poisoned_lines = poisoned.splitlines(keepends=True)
    fences = [i for i, line in enumerate(poisoned_lines) if line.rstrip("\r\n") == FENCE]
    assert len(fences) == 2, "the poisoned source no longer has exactly two fences"
    assert INJECTED_HAND_OFF_LINE in "".join(
        poisoned_lines[fences[0] + 1 : fences[1]]
    ), "the injected line did not land inside the fenced block"

    dirty = tmp_path / "dirty"
    dirty.mkdir()
    with pytest.raises(pns.Refusal) as caught:
        pns.publish(poisoned, dirty)
    assert caught.value.reason == "secret_literal"
    assert list(dirty.iterdir()) == [], "a refused publish left a file behind"


# ---------------------------------------------------------------------------
# THE REFUSAL DETAIL REPORTS A MATCH SPAN, WHICH IS NOT A TOKEN LENGTH
# ---------------------------------------------------------------------------
#
# There is NO right boundary, deliberately, and the decision is measured rather
# than assumed. A right lookahead of `(?![A-Za-z0-9_\-])` was tried against the
# `xoxb-` row, whose body class excludes `_`:
#
#     xoxb- + 16 digits + "_tail"           no right boundary -> caught
#                                           right boundary    -> MISSED
#     xoxb- + 30 digits + "-secret_li"      no right boundary -> caught
#                                           right boundary    -> MISSED
#     xoxb- + 30 digits + ".json"           both              -> caught
#
# Two of three detections lost. The greedy body already consumes maximally, so a
# right boundary cannot SHORTEN a span either - it can only refuse the match
# outright when the next character is one the body class did not accept. It buys
# nothing and costs detections, so it is rejected.
#
# What was wrong was the REPORT, not the pattern. The old detail read
# "(prefix 'ghp_', 55 chars)", which a reader takes for the credential's length.
# It is the MATCH SPAN, and the span runs to the end of the vendor's own
# alphabet: prose glued on by a hyphen or an underscore is inside that alphabet
# and is counted. Measured: a 34-character token followed by "-secret_literal
# _notes" reports 55. The number still separates a 16-character hit from a long
# one, so it stays - relabelled as the upper bound it is.


def test_the_refusal_reports_the_match_span_as_an_upper_bound():
    """The detail names a SPAN, and says so. Body is repeated capital C."""
    body = "C" * 30
    payload = "ghp_" + body + "-secret_literal_notes"
    with pytest.raises(pns.Refusal) as caught:
        pns.extract_prompt(_block(payload))

    detail = caught.value.detail
    assert "match spans" in detail, "the detail no longer says the number is a span"
    assert "UPPER BOUND" in detail, "the detail no longer says the span overstates"
    assert body not in detail, "the refusal echoed the credential"
    assert str(len(payload)) in detail, "the detail does not carry the measured span"
    assert len(payload) > len("ghp_" + body), (
        "the probe no longer overstates, so this arm has lost its subject"
    )


def test_a_right_boundary_would_lose_detections_and_is_why_there_is_none():
    """The measurement behind the rejection above, kept as an arm.

    Anyone who reaches for a right boundary to fix the span gets a red test
    naming the two detections it costs, rather than a comment they can skim.
    """
    import re

    vendor = next(v for v in pns.VENDOR_TOKENS if v.prefix == "xoxb-")
    lost = "xoxb-" + "1" * 16 + "_tail"
    kept = "xoxb-" + "1" * 16 + ".json"

    assert pns.scan_for_leaks(lost) != [], "the probe is no longer caught at all"
    assert pns.scan_for_leaks(kept) != []

    with_right = re.compile(vendor.pattern() + r"(?![A-Za-z0-9_\-])")
    assert with_right.search(lost) is None, (
        "a right boundary no longer costs this detection; re-measure the trade "
        "before adopting one"
    )
    assert with_right.search(kept) is not None


# ---------------------------------------------------------------------------
# THE NAME-VALUE SEPARATOR, AT THE GATE THAT WRITES BYTES
# ---------------------------------------------------------------------------
#
# THE DEFECT WAS PRE-EXISTING AT HEAD 69e4e9d and not introduced by the repairs
# that landed beside it. The gap between a rostered name and its value admitted
# exactly ONE optional double quote and a SINGLE colon or equals, so a name
# wrapped in backticks, a bold name, a markdown table row, a single-quoted dict
# or YAML key, `?=`, `+=` and `->` all walked the whole publish path and put the
# body on disk. Measured through THIS function, into `tmp_path`, with a dummy
# body of forty repeated `D`.
#
# WHY THESE ARMS END AT A FILE. `scan_for_leaks` is where the rule lives, but
# `publish` is where the leak ENDED - a file outside the repository, pasted by
# hand into cold sessions. `tmp_path` stands in for the Desktop; the real ritual
# is never pointed at a test directory, and the module's `--desktop` override is
# what makes that substitution possible.
#
# The probe sets are IMPORTED rather than restated. They are one population and
# the two modules must not drift into disagreeing about what is in scope.

from tests.test_no_secret_literals import (  # noqa: E402
    OUT_OF_SCOPE_BINDINGS,
    SEPARATOR_DUMMY,
    SEPARATOR_EXEMPT,
    SEPARATOR_PROBES,
)


def test_the_imported_separator_probe_sets_are_not_empty():
    """The floor. An emptied import parametrizes to nothing, which pytest
    reports as `1 skipped` at exit 0 - a pass to anyone reading the code.
    """
    assert len(SEPARATOR_PROBES) == 16
    assert len(OUT_OF_SCOPE_BINDINGS) == 5
    assert len(SEPARATOR_EXEMPT) == 7
    assert set(SEPARATOR_DUMMY) == {"D"}, "the dummy body stopped being a dummy"


@pytest.mark.parametrize(
    ("name", "text"),
    SEPARATOR_PROBES,
    ids=[name for name, _ in SEPARATOR_PROBES],
)
def test_no_in_scope_separator_survives_a_real_publish(name, text, tmp_path):
    """Refused, and NOTHING WRITTEN. The second assertion is the one that would
    have caught the defect: nine of these sixteen rows published, and the file
    on disk is what a refusal that only logs looks like from the outside.
    """
    with pytest.raises(pns.Refusal) as caught:
        pns.publish(_block("note " + text), tmp_path)
    assert caught.value.reason == "secret_literal", name + " was not refused"
    assert list(tmp_path.iterdir()) == [], (
        "a refused publish left a file behind for " + name
    )


@pytest.mark.parametrize(
    ("name", "text"),
    SEPARATOR_EXEMPT,
    ids=[name for name, _ in SEPARATOR_EXEMPT],
)
def test_an_environment_lookup_still_publishes_after_the_widening(
    name, text, tmp_path
):
    """NON-VACUITY AT THE GATE. A separator class that refused everything would
    pass every arm above and be worthless, and an over-firing hand-off gate is
    how an operator ends up switching a gate off. Each row here is a LOOKUP -
    the CORRECT destination of the rule - and each must reach disk.
    """
    report = pns.publish(_source_with(_block_body(text)), tmp_path)
    assert report["ok"] is True, "the widening refused a lookup: " + name
    written = (tmp_path / pns.TARGET_NAME).read_text(encoding="ascii")
    assert text in written, "the published bytes are not the block that went in"


@pytest.mark.parametrize(
    ("name", "text"),
    OUT_OF_SCOPE_BINDINGS,
    ids=[name for name, _ in OUT_OF_SCOPE_BINDINGS],
)
def test_the_out_of_scope_shapes_still_publish_and_the_cost_is_pinned_here(
    name, text, tmp_path
):
    """THE COST ARM, and it is deliberately uncomfortable reading. Each of these
    PUBLISHES, with the dummy body on disk.

    Two different holes, neither of them a separator question:

      A. NO OPERATOR AT ALL - the name, an English word, the value. Catching it
         needs a proximity-or-entropy rule, a different detector class with its
         own false-positive budget, and an adversary ranks it the MOST plausible
         shape in an agent-written hand-off.
      B. OFF-ROSTER NAMES bound to a value carrying no vendor prefix. The name
         path iterates `SECRET_NAMES` and the prefix path iterates
         `VENDOR_TOKENS`; such a line is in neither, by construction. That is a
         roster-completeness question.

    Pinned at the reading MEASURED rather than the reading wanted, so that
    closing either one is a decision somebody makes rather than a drift.
    """
    report = pns.publish(_source_with(_block_body(text)), tmp_path)
    assert report["ok"] is True, name + " changed reading without a ruling"
    written = (tmp_path / pns.TARGET_NAME).read_text(encoding="ascii")
    assert SEPARATOR_DUMMY in written, (
        "the dummy did NOT reach disk, so this cost arm has lost its subject "
        "and the hole it records may already be closed: re-measure before "
        "deleting it"
    )


def test_the_repo_hand_off_still_publishes_under_the_widened_separator(tmp_path):
    """The real artifact, through the real gate: if the tree's OWN hand-off is
    refused, the widening is wrong, because a gate that refuses the real artifact
    is a gate an operator switches off.

    AND THE ARM SAYS WHAT IT CANNOT PROVE. The brief for this repair asserted
    that `NEXT_SESSION_PROMPT.md` mentions rostered names in prose. MEASURED
    2026-09-11, it does not: all six names occur ZERO times in the file. So with
    respect to the SEPARATOR this arm is vacuous - it has no binding to be wrong
    about - and that was confirmed by mutation rather than assumed: making the
    binding operator optional, which is the step from a syntax rule to a
    proximity heuristic, turned the TRACKED-CORPUS arm red and left this one
    green. The count is asserted below so that the day a rostered name enters
    the hand-off, this arm's meaning changes VISIBLY instead of silently
    becoming load-bearing.

    The corpus arm in `tests/test_no_secret_literals.py` is what actually
    carries the false-positive budget. This one carries the publish path.
    """
    source = (REPO_ROOT / "NEXT_SESSION_PROMPT.md").read_text(encoding="utf-8")
    block = pns.extract_prompt(source)
    mentioned = {name: block.count(name) for name in pns.SECRET_NAMES}
    assert sum(mentioned.values()) == 0, (
        "the hand-off now mentions a rostered name, so this arm has STOPPED "
        "being vacuous about the separator and its docstring is out of date: "
        + repr({k: v for k, v in mentioned.items() if v})
    )
    assert pns.scan_for_leaks(block) == [], (
        "the widened separator refuses the tree's own hand-off block"
    )
    report = pns.publish(source, tmp_path)
    assert report["ok"] is True
    assert (tmp_path / pns.TARGET_NAME).read_text(encoding="ascii").isascii()


def test_the_two_detectors_agree_on_every_separator_probe():
    """ZERO DISAGREEMENTS, over the whole probe population at once.

    Agreement here is not two opinions coinciding - they share ONE separator
    constant, which is the point. This arm is what goes red if somebody
    re-introduces a second hand-maintained copy, which is what the defect was
    made of.
    """
    from tests.test_no_secret_literals import scan_text

    rows = (
        [(n, t, True) for n, t in SEPARATOR_PROBES]
        + [(n, t, False) for n, t in OUT_OF_SCOPE_BINDINGS]
        + [(n, t, False) for n, t in SEPARATOR_EXEMPT]
    )
    assert len(rows) == 28
    disagreements = [
        name
        for name, text, _ in rows
        if bool(pns.scan_for_leaks(text)) != bool(scan_text(text))
    ]
    assert disagreements == [], "the publisher and the sweep disagree at " + repr(
        disagreements
    )
    wrong = [
        name
        for name, text, expected in rows
        if bool(pns.scan_for_leaks(text)) is not expected
    ]
    assert wrong == [], "a probe changed reading: " + repr(wrong)
