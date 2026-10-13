"""Every ui-auditor routing must defer to the ui-audit skip list.

WHY THIS EXISTS (slice 0y, session 71 residue (b)). `.claude/agents/builder.md`
said, unconditionally, that a slice touching `surface/` or `shell/` is not
committable until `ui-auditor` has run. `.claude/commands/ui-audit.md`, under
its heading "When to skip this entirely", exempts version and dependency bumps
that change no markup, no stylesheet and no rendered string. The two rules
contradicted each other, and the 0u electron bump (a `shell/` diff that renders
nothing) needed an adjudicator waiver to get past the builder's wording. 0u is
do-not-re-litigate: the waiver stands, reversed only by narrowing that
exemption, a MAIN ruling, or a rendered regression.

The guard: every paragraph in `.claude/agents/*.md` and `.claude/commands/*.md`
that routes a `surface/` or `shell/` change to `ui-auditor` must also point at
the skip list in `.claude/commands/ui-audit.md`. The 0y adversary found the
sibling: `planner.md` carried the same unconditional rule, so the scan covers
the whole roster and command set, not one file.

Non-vacuity arms feed the pre-fix wording to the same detector and assert it
is caught; a neighbour arm asserts the routing itself survived (the fix must
not be "delete the rule").
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILDER_MD = REPO_ROOT / ".claude" / "agents" / "builder.md"
UI_AUDIT_MD = REPO_ROOT / ".claude" / "commands" / "ui-audit.md"
AGENT_AND_COMMAND_DOCS = sorted(
    [*REPO_ROOT.glob(".claude/agents/*.md"), *REPO_ROOT.glob(".claude/commands/*.md")]
)

SKIP_HEADING = "When to skip this entirely"
SKIP_POINTER = ".claude/commands/ui-audit.md"

#: The builder.md wording before slice 0y, verbatim. The non-vacuity arms
#: prove the detector rejects exactly this shape.
PRE_FIX_PARAGRAPH = (
    "Run the suites once from the repo root, separately, and trust the exit code."
    " Never re-read\nan edit to confirm it. `write_text` converts LF to CRLF on"
    " Windows; write bytes where byte\ncounts matter (`.gitattributes` pins"
    " `eol=lf`). A slice touching `surface/` or `shell/` is\nnot committable until"
    " `ui-auditor` has run and every MUST-FIX is closed.\n"
)


def _body(text: str) -> str:
    """Drop YAML frontmatter.

    A justified exemption by SHAPE, not a per-file one: the frontmatter
    `description:` is the registry blurb naming an agent's own scope
    (ui-auditor.md says "Audits surface/ and shell/"), not a routing rule, and
    `tests/test_agent_roster.py` pins its shape.
    """
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5 :].lstrip("\n")
    return text


def _paragraphs(text: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", _body(text)) if p.strip()]


#: Every token that routes a change to the visual audit: the agent name, the
#: slash command, and its pass verdict. The slash command is matched only in
#: its invocation shape - NOT preceded by a word character, `/`, `.` or `-` -
#: so the file pointer `.claude/commands/ui-audit.md` (which contains the
#: substring "/ui-audit") is not itself read as a routing. Slice 0y F1: the
#: first detector matched only "ui-auditor" and missed the orchestrated-run.md
#: merge check, which routes by `/ui-audit` and `AUDIT: PASS`.
ROUTING_TOKEN = re.compile(r"ui-auditor|(?<![\w/.-])/ui-audit\b|AUDIT: PASS")


def _routes_to_ui_auditor(paragraph: str) -> bool:
    return bool(ROUTING_TOKEN.search(paragraph)) and (
        "surface/" in paragraph or "shell/" in paragraph
    )


def unconditional_routings(text: str, *, is_skip_list_file: bool = False) -> list[str]:
    """Paragraphs routing surface/ or shell/ to ui-auditor with no skip-list citation.

    A citation is the section heading plus the file pointer. Inside ui-audit.md
    itself the pointer is implicit, so the heading alone cites the list there.
    """
    return [
        p
        for p in _paragraphs(text)
        if _routes_to_ui_auditor(p)
        and not (SKIP_HEADING in p and (is_skip_list_file or SKIP_POINTER in p))
    ]


def test_skip_list_target_exists_and_covers_dependency_bumps() -> None:
    """The pointer must not dangle, and the 0u exemption must still be there."""
    text = UI_AUDIT_MD.read_text(encoding="utf-8")
    assert f"## {SKIP_HEADING}" in text
    section = text.split(f"## {SKIP_HEADING}", 1)[1].split("\n## ", 1)[0]
    assert "dependency bumps" in section
    assert "`shell/`" in section and "`surface/`" in section


def test_scan_corpus_covers_builder_planner_and_the_skip_list() -> None:
    names = {p.name for p in AGENT_AND_COMMAND_DOCS}
    assert {"builder.md", "planner.md", "ui-auditor.md", "ui-audit.md"} <= names


def test_every_ui_auditor_routing_defers_to_ui_audit_skip_list() -> None:
    offenders = {}
    for path in AGENT_AND_COMMAND_DOCS:
        found = unconditional_routings(
            path.read_text(encoding="utf-8"), is_skip_list_file=path == UI_AUDIT_MD
        )
        if found:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = found
    assert offenders == {}, (
        "these files route surface/ or shell/ to ui-auditor unconditionally;"
        f" point them at the '{SKIP_HEADING}' list in {SKIP_POINTER}: {offenders!r}"
    )


def test_builder_still_routes_rendered_changes_to_ui_auditor() -> None:
    """Neighbour arm: the fix narrows the rule, it must not delete it."""
    text = BUILDER_MD.read_text(encoding="utf-8")
    assert any(_routes_to_ui_auditor(p) for p in _paragraphs(text))
    assert "MUST-FIX" in text


def test_detector_rejects_the_pre_fix_wording() -> None:
    """Non-vacuity arm: the detector fires on the wording slice 0y replaced."""
    assert unconditional_routings(PRE_FIX_PARAGRAPH) == [PRE_FIX_PARAGRAPH]


def test_frontmatter_strip_does_not_hide_a_body_routing() -> None:
    """Non-vacuity for the frontmatter exemption: only the frontmatter is dropped."""
    doc = (
        "---\nname: x\ndescription: Audits surface/ via ui-auditor.\n---\n\n"
        + PRE_FIX_PARAGRAPH
    )
    assert unconditional_routings(doc) == [PRE_FIX_PARAGRAPH]


def test_heading_alone_cites_the_list_only_inside_ui_audit_md() -> None:
    para = PRE_FIX_PARAGRAPH + f"Unless {SKIP_HEADING} applies.\n"
    assert unconditional_routings(para, is_skip_list_file=True) == []
    assert unconditional_routings(para) == [para]


def test_detector_requires_both_pointer_and_heading() -> None:
    """A bare file mention without the section name is still unconditional."""
    half = PRE_FIX_PARAGRAPH + "See `.claude/commands/ui-audit.md`.\n"
    assert unconditional_routings(half) == [half]


#: The orchestrated-run.md merge-check wording before 0y F1, verbatim. It
#: routes by the slash command and the verdict, never naming ui-auditor.
PRE_F1_MERGE_CHECK = (
    "- If any slice touched `surface/` or `shell/`, also run\n"
    "  `python scripts/qa_companion.py` and `cd shell && node --test`, and confirm\n"
    "  that `/ui-audit` already ran and returned `AUDIT: PASS` INSIDE that slice.\n"
    "  Per `.claude/commands/ui-audit.md`, the audit runs before the commit, so\n"
    "  discovering at merge time that it never ran is a process failure to report,\n"
    "  not a step to run late.\n"
)


def test_detector_rejects_the_pre_f1_merge_check() -> None:
    """Non-vacuity arm (0y F1): a `/ui-audit` + `AUDIT: PASS` routing is caught."""
    assert unconditional_routings(PRE_F1_MERGE_CHECK) == [PRE_F1_MERGE_CHECK]


def test_each_routing_token_alone_is_detected() -> None:
    for token in ("ui-auditor", "`/ui-audit`", "run /ui-audit", "AUDIT: PASS"):
        para = f"A `surface/` slice needs {token} before the commit.\n"
        assert unconditional_routings(para) == [para], token


def test_file_pointer_alone_is_not_a_routing() -> None:
    """The allowance: `.claude/commands/ui-audit.md` is a pointer, not a routing.

    Paired with test_each_routing_token_alone_is_detected, which proves the
    slash-command form is still caught.
    """
    para = "A `surface/` change: see `.claude/commands/ui-audit.md` for the phases.\n"
    assert unconditional_routings(para) == []
