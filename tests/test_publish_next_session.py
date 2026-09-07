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
# Added 2026-09-07 after Legion Wallpaper asked whether anyone gated the
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
