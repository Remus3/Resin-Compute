"""Attended sends and /done go through `tools/send_note.py` - and nothing else.

WHY THIS EXISTS (hand-off 0w, session 71). 0q landed `tools/send_note.py`,
the attended send path that writes the outbound-ledger row FLEET-COMMON item
14c's `OutboundCap` counts, plus its `audit`. Nothing forced an attended
session or /done to use it: the two command docs that tell a session how to
work (`.claude/commands/done.md`, `.claude/commands/orchestrated-run.md`)
never named it, so a hand-written send - the note copied into the
recipient's inbox and this tree's own - could still skip the row. That is
exactly how both notes of 2026-10-12 went unrecorded.

WHAT IS GUARDED.

  1. Both docs name `python tools/send_note.py send` as the send path.
  2. done.md carries the `python tools/send_note.py audit` step in a section
     that says it must print nothing.
  3. Every claim-block in either doc that describes sending a note names
     `tools/send_note.py`, and no block describes a manual send (copying or
     writing a note into an inbox, appending the ledger by hand,
     `cap.record`).
  4. Every `tools/send_note.py <sub>` the docs cite is a subcommand the
     module's own argparse declares - PARSED from the source, never restated.

A claim-block is a blank-line paragraph split further at each list bullet,
the unit `tests/test_docs_hook_commands.py` established. Every checker
returns `(checked, offenders)` and every arm asserts the checked count first:
zero out of zero is not a pass. Every sweep carries two guards - the bad
text is caught AND the legitimate neighbour (an "anything outbound" licence
line, a send through the tool) survives. Mutation arms drive the checkers
with planted in-memory text; nothing here writes to the tree.

0q RULING B is not re-litigated here: an over-cap send still records its
row (`over-cap-recorded`). The docs may say so; nothing below forbids it.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DONE_MD = REPO_ROOT / ".claude" / "commands" / "done.md"
ORCH_MD = REPO_ROOT / ".claude" / "commands" / "orchestrated-run.md"
SEND_NOTE = REPO_ROOT / "tools" / "send_note.py"
GUARDED = (DONE_MD, ORCH_MD)

TOOL = "tools/send_note.py"
SEND_CMD = "python tools/send_note.py send"
AUDIT_CMD = "python tools/send_note.py audit"

#: A block DESCRIBES A SEND when it talks about sending / delivering a note,
#: an outbound note, the outbound ledger file, or an inbox copy.
_DESCRIBES_SEND = re.compile(
    r"\b(send|sends|sending|sent|deliver|delivers|delivered|delivering)\b[^.\n]{0,60}\bnotes?\b"
    r"|\bnotes?\b[^.\n]{0,40}\b(send|sends|sending|sent|deliver|delivered)\b"
    r"|\boutbound[- ]notes?\b"
    r"|outbound_notes\.jsonl"
    r"|moon_sync_inbox",
    re.IGNORECASE,
)

#: A MANUAL send, forbidden in either doc whatever else the block says.
_MANUAL_SEND = re.compile(
    r"\b(copy|copies|copying|write|writes|writing|drop|drops|place|places|put|puts|move|moves)\b"
    r"[^.\n]{0,60}\b(into|to|in)\b[^.\n]{0,30}\b(recipient'?s?|their|destination|sibling'?s?)\b"
    r"[^.\n]{0,20}\binbox"
    r"|\bcap\.record\b"
    r"|\b(append|appends|appending|add|adds|write|writes)\b[^.\n]{0,40}outbound_notes\.jsonl"
    r"|\bCopy-Item\b[^\n]*moon_sync_inbox"
    r"|\bcp\b[^\n]*moon_sync_inbox"
    r"|\bby hand\b[^.\n]{0,40}\b(inbox|ledger|row)\b",
    re.IGNORECASE,
)

_PRINTS_NOTHING = re.compile(r"\b(must\s+)?prints?\s+nothing\b", re.IGNORECASE)
_CITED_SUB = re.compile(r"tools/send_note\.py\s+([a-z][a-z-]*)")
_BULLET = re.compile(r"^\s*(?:[-*]|\d+\.)\s+")


def claim_blocks(text: str) -> list[str]:
    """Blank-line paragraphs, split further at each list bullet."""
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if not line.strip() or _BULLET.match(line):
            if current:
                blocks.append("\n".join(current))
            current = [line] if line.strip() else []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def sections(text: str) -> list[str]:
    """Text split at each markdown heading line."""
    return [s for s in re.split(r"(?m)^(?=#{1,6} )", text) if s.strip()]


def check_send_blocks(text: str) -> tuple[int, list[str]]:
    """(blocks that describe a send, offenders). An offender either
    describes a send without naming the tool, or describes a manual send."""
    checked = 0
    offenders: list[str] = []
    for block in claim_blocks(text):
        manual = _MANUAL_SEND.search(block)
        if manual:
            offenders.append(f"manual send path: {manual.group(0)!r}")
        if _DESCRIBES_SEND.search(block):
            checked += 1
            if TOOL not in block:
                offenders.append(f"send described without {TOOL}: {block.strip()[:120]!r}")
    return checked, offenders


def check_audit_step(text: str) -> tuple[int, list[str]]:
    """(sections citing the audit command, offenders). Pass needs at least
    one section that cites it AND says it must print nothing."""
    citing = [s for s in sections(text) if AUDIT_CMD in s]
    if not citing:
        return 0, [f"no section cites {AUDIT_CMD!r}"]
    if not any(_PRINTS_NOTHING.search(s) for s in citing):
        return len(citing), ["the audit step never says it must print nothing"]
    return len(citing), []


def declared_subcommands() -> set[str]:
    """The subcommands `tools/send_note.py` declares, parsed from its source."""
    return set(re.findall(r'add_parser\(\s*"([a-z][a-z-]*)"', SEND_NOTE.read_text(encoding="utf-8")))


def check_cited_subcommands(text: str, declared: set[str]) -> tuple[int, list[str]]:
    cited = _CITED_SUB.findall(text)
    return len(cited), sorted({c for c in cited if c not in declared})


_SPAN = re.compile(r"`([^`\n]+)`")
_FLAG = re.compile(r"(?<![A-Za-z0-9-])--[a-z][a-z-]*")
_TOKEN = re.compile(r"[a-z][a-z]*(?:-[a-z]+)*")


def declared_flags(source: str) -> set[str]:
    """Every `--flag` the module's argparse declares, parsed from source."""
    return set(re.findall(r'add_argument\(\s*"(--[a-z][a-z-]*)"', source))


def check_cited_flags(text: str, flags: set[str]) -> tuple[int, list[str]]:
    """(flags cited in a backtick span naming the tool, undeclared ones)."""
    cited = [f for span in _SPAN.findall(text) if TOOL in span for f in _FLAG.findall(span)]
    return len(cited), sorted({f for f in cited if f not in flags})


def cited_tokens(text: str) -> list[str]:
    """Every bare lowercase backticked token (a result `reason`, a row key,
    a kit method) in a claim-block that names the tool."""
    out: list[str] = []
    for block in claim_blocks(text):
        if TOOL not in block:
            continue
        out.extend(s for s in _SPAN.findall(block) if _TOKEN.fullmatch(s))
    return out


def check_cited_tokens(text: str, source: str) -> tuple[int, list[str]]:
    """(tokens cited, tokens the module does not carry). A token is carried
    when it is a quoted string literal in the source - so deleting a reason
    the docs promise reds here - or a method the source calls (`.record(`)."""
    cited = cited_tokens(text)
    missing = sorted({
        t for t in cited
        if f'"{t}"' not in source and not re.search(r"\." + re.escape(t) + r"\(", source)
    })
    return len(cited), missing


# ---------------------------------------------------------------- live docs


def test_send_note_declares_send_and_audit() -> None:
    declared = declared_subcommands()
    assert {"send", "audit"} <= declared, f"tools/send_note.py declares {sorted(declared)}"


def test_both_docs_name_the_send_command() -> None:
    missing = [p.name for p in GUARDED if SEND_CMD not in p.read_text(encoding="utf-8")]
    assert missing == [], f"{missing} never name {SEND_CMD!r} as the send path"


def test_done_md_carries_the_audit_must_print_nothing_step() -> None:
    checked, offenders = check_audit_step(DONE_MD.read_text(encoding="utf-8"))
    assert checked >= 1, offenders
    assert offenders == [], offenders


def test_every_send_description_goes_through_send_note() -> None:
    for path in GUARDED:
        checked, offenders = check_send_blocks(path.read_text(encoding="utf-8"))
        assert checked >= 1, f"{path.name}: zero send-describing blocks examined"
        assert offenders == [], f"{path.name}: {offenders}"


def test_cited_subcommands_exist() -> None:
    declared = declared_subcommands()
    for path in GUARDED:
        checked, unknown = check_cited_subcommands(path.read_text(encoding="utf-8"), declared)
        assert checked >= 1, f"{path.name}: cites no tools/send_note.py subcommand"
        assert unknown == [], f"{path.name} cites undeclared subcommands {unknown}"


def test_cited_flags_exist() -> None:
    flags = declared_flags(SEND_NOTE.read_text(encoding="utf-8"))
    assert "--apply" in flags, f"tools/send_note.py declares {sorted(flags)}"
    checked, unknown = check_cited_flags(DONE_MD.read_text(encoding="utf-8"), flags)
    assert checked >= 1, "done.md cites no tools/send_note.py flag"
    for path in GUARDED:
        _checked, unknown = check_cited_flags(path.read_text(encoding="utf-8"), flags)
        assert unknown == [], f"{path.name} cites undeclared flags {unknown}"


def test_cited_reason_tokens_exist() -> None:
    source = SEND_NOTE.read_text(encoding="utf-8")
    checked, missing = check_cited_tokens(DONE_MD.read_text(encoding="utf-8"), source)
    cited = set(cited_tokens(DONE_MD.read_text(encoding="utf-8")))
    promised = {"over-cap-recorded", "undelivered", "recipient-mismatch", "unknown-recipient"}
    assert promised <= cited, f"done.md no longer cites {sorted(promised - cited)}"
    assert checked >= len(promised)
    assert missing == [], f"done.md cites tokens tools/send_note.py does not carry: {missing}"
    for path in GUARDED:
        _checked, missing = check_cited_tokens(path.read_text(encoding="utf-8"), source)
        assert missing == [], f"{path.name}: {missing}"


# ---------------------------------------------------------- non-vacuity arms


def test_arm_flag_mutant_is_caught() -> None:
    """The adversary's mutant: `--apply` deleted from the argparse."""
    source = SEND_NOTE.read_text(encoding="utf-8")
    mutant = source.replace('p_audit.add_argument("--apply", action="store_true")\n', "")
    assert mutant != source, "mutation site moved; re-aim the arm"
    doc = DONE_MD.read_text(encoding="utf-8")
    assert check_cited_flags(doc, declared_flags(mutant))[1] == ["--apply"]
    assert check_cited_flags(doc, declared_flags(source))[1] == []


def test_arm_reason_mutant_is_caught() -> None:
    source = SEND_NOTE.read_text(encoding="utf-8")
    mutant = source.replace('"over-cap-recorded"', '"over-cap-forced"')
    assert mutant != source, "mutation site moved; re-aim the arm"
    doc = DONE_MD.read_text(encoding="utf-8")
    assert check_cited_tokens(doc, mutant)[1] == ["over-cap-recorded"]
    assert check_cited_tokens(doc, source)[1] == []


def test_neighbour_prose_token_outside_tool_block_survives() -> None:
    planted = "Run `pytest` and read `ruff` output.\n"
    assert check_cited_tokens(planted, "") == (0, [])


def test_arm_manual_copy_into_inbox_is_caught() -> None:
    planted = "Send the note by copying it into the recipient's inbox, then our own.\n"
    checked, offenders = check_send_blocks(planted)
    assert checked == 1
    assert len(offenders) == 2, offenders


def test_arm_hand_appended_ledger_row_is_caught() -> None:
    planted = "After a send, append the row to outbound_notes.jsonl yourself.\n"
    _checked, offenders = check_send_blocks(planted)
    assert any("manual send path" in o for o in offenders), offenders


def test_arm_cap_record_is_caught() -> None:
    _checked, offenders = check_send_blocks("Then call cap.record for the outbound note.\n")
    assert any("cap.record" in o for o in offenders), offenders


def test_arm_send_without_tool_is_caught() -> None:
    _checked, offenders = check_send_blocks("- Send any reply note to MAIN before the commit.\n")
    assert any("without" in o for o in offenders), offenders


def test_neighbour_send_through_tool_survives() -> None:
    planted = "- Send every note with `python tools/send_note.py send <draft>`.\n"
    checked, offenders = check_send_blocks(planted)
    assert checked == 1
    assert offenders == []


def test_neighbour_outbound_licence_line_survives() -> None:
    planted = (
        "- **If the work touches game data, a data source or anything outbound, dispatch\n"
        "  `researcher` FIRST and treat its gate as blocking.**\n"
    )
    checked, offenders = check_send_blocks(planted)
    assert (checked, offenders) == (0, [])


def test_arm_audit_missing_is_caught() -> None:
    checked, offenders = check_audit_step("## 9. Marker\n\nNothing about notes.\n")
    assert checked == 0 and offenders


def test_arm_audit_without_print_nothing_is_caught() -> None:
    planted = "## 4b. Audit\n\n```\npython tools/send_note.py audit\n```\n\nRecord the output.\n"
    checked, offenders = check_audit_step(planted)
    assert checked == 1 and offenders


def test_neighbour_audit_with_print_nothing_survives() -> None:
    planted = "## 4b. Audit\n\n```\npython tools/send_note.py audit\n```\n\nIt must print nothing.\n"
    assert check_audit_step(planted) == (1, [])


def test_arm_undeclared_subcommand_is_caught() -> None:
    checked, unknown = check_cited_subcommands("run `python tools/send_note.py deliver x`", {"send", "audit"})
    assert (checked, unknown) == (1, ["deliver"])
