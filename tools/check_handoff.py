"""Gate the next-session hand-off's CONTENT before `/done` calls it ready.

`RSC-NEXT-SESSION.txt` in the repo root is the hand-off (FLEET-COMMON item 5),
TRACKED IN A PUBLIC REPOSITORY, read by every cold session and quoted into
notes to sibling trees. This module reads it and refuses it when it is:

- TRUNCATED - under `MIN_BYTES`. A truncated hand-off and a complete one both
  read as current; only one is missing the context that makes it useful.
- NON-ASCII - the CLAUDE.md hard rule, named by codepoint.
- AMBIGUOUS - more than one fenced block. A raw, fence-less file is the whole
  hand-off; a single fenced block is unwrapped.
- LEAKING - a credential or an absolute path naming a real user profile. The
  refusal never echoes what it caught.
- MISCOUNTED - no single readable column-0 `SESSION: <n>` line (FLEET-COMMON
  item 13). `/done` writes n+1, so a guessed counter would become permanent.
  The parser is `tools/session_checklist.py`'s own, imported, never restated.

MOVED HERE 2026-10-08 from `tools/publish_next_session.py`, which also
converged an operator shortcut onto this file. MAIN's 2246 ORDER (FLEET-KIT v13,
section 1) retired that shortcut with FLEET-COMMON item 5; the content rules
were moved first and are byte-for-byte the same detectors, so the sweep in
`tests/test_no_secret_literals.py` still imports its single source from here.
This module READS ONE FILE AND WRITES NOTHING.

Usage:
    python tools/check_handoff.py            # gate RSC-NEXT-SESSION.txt
    python tools/check_handoff.py <file>     # gate another file (tests)

Exit 0 and one `check_handoff: ok ...` line when clean; exit 1 and one
`check_handoff: REFUSED <reason> - <detail>` line otherwise. No message names
a directory.
"""

from __future__ import annotations

import argparse
import importlib
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "RSC-NEXT-SESSION.txt"

# THE BOOTSTRAP IS LOAD-BEARING. Run as `python tools/check_handoff.py`,
# `sys.path[0]` is `tools/` and the package import below would raise
# `ModuleNotFoundError`; under pytest the root is already on the path and no
# in-process arm can see that. `tests/test_check_handoff.py` drives the real
# command line from another directory for exactly this.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# BY importlib AND NOT A STATIC IMPORT: mypy checks `tools/` files as top-level
# modules, so a static `tools.session_checklist` import makes that file "found
# twice under different module names" and stops mypy dead (measured
# 2026-10-08). `tools/moon_sync_responder.py` imports this module the same way.
session_number: Callable[[str], int | None] = importlib.import_module(
    "tools.session_checklist"
).session_number

FENCE = "`" * 3

# The hand-off has never been under a few thousand bytes. Anything near this
# floor is a truncation or a stub, not a prompt.
MIN_BYTES = 2000

#: THE HAND-OFF IS A PUBLICATION SURFACE, and until 2026-09-07 this gate did
#: not treat it as one. It refused non-ASCII and truncation - both real - and
#: passed a live API key and an absolute path naming the operator's account
#: straight through to publication. Measured, not theorised: a block carrying
#: an inline Nimble key, and one carrying
#: `C:\Users\<account>\AppData\...` were each published clean.
#:
#: Why that matters more here than in an ordinary file. The hand-off is pasted
#: by hand into a cold session, quoted into notes to four sibling repos, and
#: `RSC-NEXT-SESSION.txt` is TRACKED in a PUBLIC repository. Sibling-E
#: raised exactly this and asked whether anyone gated PII more widely; this
#: tree's honest answer was no. `tests/test_machine_identity.py` sweeps tracked
#: files and `tests/test_no_secret_literals.py` sweeps them for credentials,
#: but both run over the COMMITTED tree - neither sees a block on its way out
#: for publication, which is the one path that leaves the toolchain.
#:
#: Vendor prefixes only, deliberately. A digest, a git SHA and a base64 blob
#: all look random; only a real credential carries one of these.
#:
#: THE DIRECTION OF THE DEPENDENCY, corrected 2026-09-11. This list and the one
#: in `tests/test_no_secret_literals.py` were STATED IN BOTH PLACES, because a
#: hand-off gate that imported from the test suite would be a tool depending on
#: tests to run. That reasoning is right about the direction and was wrong to
#: conclude duplication: the test may import from the tool, and the two copies
#: HAD ALREADY DRIFTED. `SECRET_NAMES` and `ENV_REFERENCE` below were made the
#: single source in that pass; THE VENDOR PREFIXES WERE NOT, and were recorded
#: as "a known remaining pair" on the grounds that the two were different
#: SHAPES. Different shapes is a reason to pick one, not a reason to keep two.
#:
#: THE PAIR HAD ALREADY DRIFTED TOO, measured 2026-09-11 end to end through the
#: real publish path with NO mutation and every arm in the tree green - EIGHT
#: disagreeing cases, three of which leaked:
#:
#:     xoxb- + 24  ->  REFUSED    reason=secret_literal
#:     xoxa- + 24  ->  PUBLISHED  ok=True, token on disk
#:     xoxs- + 24  ->  PUBLISHED  ok=True, token on disk
#:
#: The sweep caught all three. The sweep runs over the COMMITTED tree; this
#: module is the only gate on the path that LEAVES the toolchain.
#:
#: THE POPULATION, derived by subtraction rather than by union. The old tuple
#: here held EIGHT prefixes and the sweep's alternation expanded to ELEVEN;
#: sweep-minus-publisher is {xoxa-, xoxr-, xoxs-} and publisher-minus-sweep is
#: EMPTY. So on the prefix axis the tuple was an incomplete transcription of the
#: same claim - `xox[bapsr]-` is one Slack family and this file had enumerated
#: two of its five spellings - and adopting all eleven is a de-duplication
#: rather than a widening.
#:
#: THE LENGTH RULE IS NEITHER LIST'S RULE, and unioning them was measured and
#: REJECTED. This file's old shape - one wide class `[A-Za-z0-9_\-]` with one
#: shared floor of 16 - applied to all eleven prefixes produces NINE false
#: positives over the 221 readable tracked files, every one of them
#: hyphen-segmented English where `sk-` is the tail of `task-`:
#: `task-argv-does-not-arm`, `task-argv-is-a-dry-run`,
#: `task-name-argument-is-dropped`. Raising that shared floor to 20 still leaves
#: one. A gate that refuses a hand-off for quoting a test id is a gate somebody
#: switches off, so the flat floor is not salvageable by raising it.
#:
#: CONTIGUITY WAS THE WRONG ANSWER TO THAT MEASUREMENT, and the wrong answer
#: opened a wider hole than it closed. It required an UNBROKEN RUN of 16 of the
#: vendor's own alphabet, with that vendor's separators allowed only in a
#: 24-character lead-in ahead of it. Measured in-process 2026-09-11 against the
#: shipped bytes, driving the real publish path into a scratchpad directory:
#:
#:     xoxb- + 13 ones + "-" + 13 twos + "-" + 24 capitals   (SYNTHETIC)
#:       scan_for_leaks -> []
#:       publish()      -> ok=True, TOKEN ON DISK
#:
#: `xoxb-` had never leaked before. Closing the three Slack spellings at the
#: FLAT body shape opened every SEGMENTED shape of all five of them.
#:
#: THE MECHANISM WAS THE LEAD-IN BOUND, NOT THE RUN. That probe's final run is
#: 24 characters - intact, 8 over the floor. Its identifier segments measured 28
#: characters, four over `MAX_LEAD`, so the matcher could not stride from the
#: prefix to the run. A credential whose secret is UNTOUCHED was refused a
#: refusal because its identifier segments were two characters too long. Over
#: the product of the eleven prefixes and four segmentation layouts - 44 tokens
#: - THIRTY were caught by an old detector and missed by both new ones.
#:
#: THE DISCRIMINATOR IS A TOKEN BOUNDARY, derived from the nine false positives
#: rather than assumed. What all nine share is not length and not segmentation:
#: in every one of them `sk-` is the tail of the English word `task-`, so the
#: character immediately before the match is a letter. The match does not start
#: where a token starts. Re-derived over the same 221 readable tracked files:
#:
#:     flat wide class, floor 16                 ->  9 hits
#:     flat wide class, floor 20                 ->  1 hit
#:     flat wide class, floor 16, LEFT BOUNDARY  ->  0 hits
#:
#: So the rule is a left boundary plus the vendor's own body class at a shared
#: floor of 16 - the LOWER of the two old floors. Nothing is given up on the
#: LENGTH axis and nothing on the SEGMENTATION axis: the vendor's separators
#: stay INSIDE its body class, which is where this tree's own prior spec had
#: them. `git show HEAD:tests/test_no_secret_literals.py` spelled Slack as
#: `xox[bapsr]-[A-Za-z0-9\-]{20,}`, hyphen inside the body at a floor of 20.
#: The contiguity rule contradicted a spec the tree already carried.
#:
#: AND IT IS ONE RULE, NOT A PER-VENDOR EXCEPTION. The contiguity rule met this
#: defect class for Riot alone and was patched for Riot alone, by widening that
#: one row's `core`; ten vendors kept the defect and nobody had a Slack,
#: Anthropic or Google sibling of that arm. A rule that needs a second
#: per-vendor patch is the wrong rule.
MIN_BODY = 16

#: A credential match must BEGIN WHERE A TOKEN BEGINS. This is the whole of the
#: discriminator, and it is what lets the body class stay wide enough to carry
#: the vendor's own separators without refusing hyphen-segmented English.
#:
#: A lookbehind rather than `\b`: `\b` is a transition between word and
#: non-word, and several prefixes here START with a non-word character run or
#: end in one, so `\b` would answer a different question at each of them.
#:
#: LETTERS ONLY, and `0-9_` is deliberately NOT in this class. The wider
#: spelling `(?<![A-Za-z0-9_])` shipped first and SILENTLY GAVE UP A WHOLE
#: CLASS: every credential whose preceding character is a digit or an
#: underscore. Measured 2026-09-11 by an adversary driving the real publish path
#: into a temp directory, bodies repeated characters and SYNTHETIC throughout -
#: `cache_` + the Anthropic prefix, `TOKEN_` + the GitHub prefix, and `v2` +
#: the GitHub prefix all scanned clean and reached disk, while
#: `git show HEAD:tools/publish_next_session.py`, which carried no lookbehind at
#: all, refused all three. A narrowing that regresses against the version it
#: replaced is not a narrowing anybody chose.
#:
#: DERIVED BY SUBTRACTION over two measured populations, not adopted. The nine
#: false positives the boundary exists to kill - re-derived this run over HEAD's
#: bytes, 221 readable files of 223 tracked - have a preceding-character census
#: of exactly {'a'}: in every one `sk-` is the tail of `task-`, so the preceding
#: character is A LETTER. The break set's preceding characters are '_', '_' and
#: '2' - an underscore and a digit. `[A-Za-z]` separates the two populations and
#: is the only tried class that does:
#:
#:     no lookbehind               ->  9 false positives, break set CAUGHT
#:     (?<![A-Za-z0-9_])           ->  0 false positives, break set MISSED
#:     (?<![A-Za-z])               ->  0 false positives, break set CAUGHT
#:
#: WHAT IT COSTS is a letter-preceded credential, at every vendor and every
#: layout. That cost is not implicit: `tests/test_no_secret_literals.py` runs a
#: census over all 128 ASCII codepoints and asserts the given-up set is EXACTLY
#: `string.ascii_letters`, and the publisher-side arm feeds one probe per class
#: through `publish()` itself. Widen this back and those arms go red naming the
#: characters the widening surrendered.
LEFT_BOUNDARY = r"(?<![A-Za-z])"


class VendorToken(NamedTuple):
    """One vendor's credential shape.

    `body` is the vendor's own alphabet INCLUDING the separators its real tokens
    carry, so a segmented credential is matched end to end rather than at
    whatever fragment happens to be contiguous.
    """

    prefix: str
    body: str

    def pattern(self) -> str:
        """The regex source for this vendor. Built, never hand-spelled twice."""
        return (
            LEFT_BOUNDARY
            + re.escape(self.prefix)
            + self.body
            + "{"
            + str(MIN_BODY)
            + ",}"
        )


#: THE SINGLE SOURCE for both detectors. `tests/test_no_secret_literals.py`
#: imports the compiled alternation below; nothing restates these.
#:
#: `sk-ant-` sits before `sk-` so the alternation names Anthropic rather than
#: the shorter prefix that also matches it.
#: EVERY ROW CARRIES ITS VENDOR'S OWN SEPARATORS, and no row is an exception to
#: the rule. Riot needed a per-vendor patch under the contiguity rule because
#: its real format is segmented 8-4-4-4-12; under a boundary rule its row is
#: shaped like every other row, which is the test of whether the rule is right.
#: The classes are grounded in this tree's own prior spec at
#: `git show HEAD:tests/test_no_secret_literals.py` - hex for Riot, alphanumeric
#: plus hyphen for Slack, alphanumeric plus underscore and hyphen for the rest -
#: and are not re-derived from memory or from a web search.
#:
#: THE TWO ANTHROPIC FAMILIES HAVE ROWS OF THEIR OWN, added 2026-10-03. Before
#: that an admin key was refused only because it also begins `sk-ant-` and
#: `sk-`: with those two generic rows removed, it matched no row at all. The
#: family rows sit ahead of `sk-ant-` so the sweep's alternation names the
#: family. ASSUMPTION, accepted by the merger: `sk-ant-admin01-` is the Admin
#: API key family as stated in the dispatch, not verified against Anthropic's
#: docs; `sk-ant-api03-` is the spelling this tree's own fixtures already plant.
VENDOR_TOKENS = (
    VendorToken("sk-ant-admin01-", r"[A-Za-z0-9_\-]"),
    VendorToken("sk-ant-api03-", r"[A-Za-z0-9_\-]"),
    VendorToken("sk-ant-", r"[A-Za-z0-9_\-]"),
    VendorToken("sk-", r"[A-Za-z0-9_\-]"),
    VendorToken("ghp_", r"[A-Za-z0-9_\-]"),
    VendorToken("github_pat_", r"[A-Za-z0-9_\-]"),
    VendorToken("AIza", r"[A-Za-z0-9_\-]"),
    VendorToken("RGAPI-", r"[0-9a-f\-]"),
    VendorToken("xoxa-", r"[A-Za-z0-9\-]"),
    VendorToken("xoxb-", r"[A-Za-z0-9\-]"),
    VendorToken("xoxp-", r"[A-Za-z0-9\-]"),
    VendorToken("xoxr-", r"[A-Za-z0-9\-]"),
    VendorToken("xoxs-", r"[A-Za-z0-9\-]"),
)

#: The sweep's entry point: one alternation over the whole table. The publisher
#: iterates `VENDOR_TOKENS` instead, because its refusal names which vendor
#: fired and an alternation cannot say.
VENDOR_TOKEN = re.compile("(?:" + "|".join(v.pattern() for v in VENDOR_TOKENS) + ")")

#: Secret-bearing variable names bound to a literal. The NAME is the evidence;
#: the value's entropy is irrelevant, which is what catches a short key.
#:
#: THE ONE COPY. `tests/test_no_secret_literals.py` IMPORTS this tuple rather
#: than restating it - see the single-source note on `ENV_REFERENCE` below for
#: why that direction, and only that direction, is allowed.
SECRET_NAMES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_USAGE_KEY",
    "NIMBLE_API_KEY",
    "GEMINI_API_KEY",
    "RIOT_API_KEY",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
)

#: The character population of a WINDOWS ENVIRONMENT VARIABLE NAME, derived by
#: subtraction from a real corpus rather than by enumerating the cases somebody
#: happened to think of. Measured on this box 2026-09-11 against this process's
#: own environment block: of 101 names, 93 match `[A-Z_]+` end to end and EIGHT
#: do not - PROGRAMW6432, PROGRAMFILES(X86), COMMONPROGRAMFILES(X86),
#: COMMONPROGRAMW6432, CUDA_PATH_V13_3, PYTHONUTF8, ASL.LOG and SENTRY-TRACE.
#: Digits, parentheses, a dot and a hyphen, in one real environment block. A
#: narrower class does not make the guard stricter; it makes it refuse eight
#: percent of the legal spellings of its own destination.
_ENV_NAME = r"[A-Za-z0-9_.()-]+"

#: Referencing the environment is the CORRECT pattern and stays legal. Anything
#: matching one of these as the bound value is a lookup, not a literal.
#:
#: THIS IS THE SINGLE SOURCE OF TRUTH, and it is here rather than in the test
#: suite on purpose. `tests/test_no_secret_literals.py` imports it. The reverse
#: is forbidden - a hand-off gate that imported from `tests/` would be a tool
#: depending on tests to run - and two hand-maintained copies is what this
#: replaced: the test's copy had closed a false positive that this file's copy
#: never heard about, with no detector between them. One object cannot drift
#: from itself, which is why this is an import and not a drift arm.
#:
#: CASE FLAGS ARE SCOPED PER ALTERNATIVE, not applied to the pattern, because
#: the alternatives are in DIFFERENT LANGUAGES. `$env:` is PowerShell and
#: `GetEnvironmentVariable` is .NET reached through PowerShell, and both resolve
#: case-insensitively, so all their spellings name one lookup. `os.environ` and
#: `getenv` are PYTHON, which is case-sensitive, and `OS.ENVIRON` is a
#: NameError rather than a variant. A blanket `re.IGNORECASE` would also fold
#: the unbraced `[A-Z_]+` form below into `[A-Za-z_]+`, and that form is
#: UNANCHORED, so `"abc$key"` - a real literal with a variable spliced in -
#: would go quiet.
#:
#: THE UNBRACED FORM IS DELIBERATELY LEFT NARROW for that same reason, and its
#: asymmetry is known rather than overlooked: `${name}` and `%name%` are
#: delimited at BOTH ends, so widening their class cannot swallow a trailing
#: literal, while `$name` is delimited at one end only. A value that is WHOLLY a
#: variable reference is handled by the anchored `VARIABLE_VALUE` instead.
#:
#: THE `$env:` ALTERNATIVE CARRIES NO CASE FLAG, AND THAT IS MEASURED RATHER
#: THAN AN OVERSIGHT. A mutation pass put `(?i:)` on it and NOTHING went red,
#: because the unbraced `\$\{?[A-Z_]+\}?` alternative below already matches the
#: leading `$E` of `$Env:` and `$ENV:`, and this literal covers the all-lowercase
#: spelling - so between them every casing is already exempt and the flag could
#: not change an answer. A flag no arm can kill is an arm that cannot fail, so
#: it was removed rather than left looking load-bearing. IF THE UNBRACED
#: ALTERNATIVE IS EVER ANCHORED OR NARROWED, this line needs the flag back.
#:
#: THE CLOSING BRACE IS REQUIRED HERE, and making it optional was tried and
#: REJECTED. The bound value used to be captured as `[^\s,}]+`, which STOPS AT
#: `}`, so an unquoted `${name}` arrived here already truncated to `${name` and
#: a required brace could never match it. Relaxing the brace made the arm pass
#: and immediately exempted a secret name bound to the quoted value
#: `"${unterminated` - no closer at all, which is a literal. The partner arm
#: caught it. (Spelled without its variable name on purpose: this file is swept
#: by `tests/test_no_secret_literals.py` and is NOT self-exempt, so a comment
#: carrying the whole binding would be an offender. Measured, not guessed - the
#: first draft of this note turned that sweep red.)
#: The capture is what was wrong, so `VALUE_CAPTURE` below was fixed instead and
#: the brace stays required: an unterminated brace is a literal, and a
#: terminated one is a lookup, and now the two are distinguishable again.
ENV_REFERENCE = re.compile(
    r"os\.environ"
    r"|getenv"
    r"|(?i:GetEnvironmentVariable)"
    r"|\$env:"
    r"|\$\{" + _ENV_NAME + r"\}"
    r"|\$\{?[A-Z_]+\}?"
    r"|%" + _ENV_NAME + r"%"
    r"|secrets\."
    r"|vars\."
    r"|MOVED-TO-"
    r"|<[^>]*>"
    r"|xxx|XXX|placeholder|PLACEHOLDER"
)

#: A bound value that IS a variable reference in its ENTIRETY - PowerShell or
#: shell `$key` - is a lookup rather than a literal. Anchored, and kept OUT of
#: `ENV_REFERENCE`, which is applied with `.search()`.
VARIABLE_VALUE = re.compile(r"^\$[A-Za-z_][A-Za-z0-9_]*$")

#: The RIGHT-HAND SIDE of a `NAME = value` binding: a quoted string, a BRACED
#: reference, or a bare run of non-delimiters. Shared with
#: `tests/test_no_secret_literals.py`, which wraps it in its own named group.
#:
#: THE BRACED ALTERNATIVE IS WHY THIS IS A CONSTANT AND NOT A LITERAL. Without
#: it the bare alternative `[^\s,}]+` truncates an unquoted `${name}` at the
#: closing brace, and the exemption downstream then cannot tell a TERMINATED
#: reference from an UNTERMINATED one - so it either over-fires on every
#: unquoted `${name}` or exempts a quoted `"${unterminated"`. Both were
#: measured here before the alternative existed. It sits BEFORE the bare run so
#: the longer, correct capture wins.
VALUE_CAPTURE = r"\"[^\"]*\"|'[^']*'|\$\{[^}\s]*\}|[^\s,}]+"

#: WHAT MAY SIT BETWEEN A ROSTERED NAME AND ITS VALUE. The shape this replaces
#: was `\"?\s*[:=]\s*` - ONE optional double quote, then a SINGLE colon or
#: equals. Anything else between the name and the value and the name loop below
#: never fired, no exemption was consulted, and the value was never examined.
#: MEASURED 2026-09-11 through the real publish path into a temp directory, with
#: a dummy body of repeated characters: a backtick-wrapped name, a bold name, a
#: markdown table row, a single-quoted dict or YAML key, `?=`, `+=` and `->` all
#: PUBLISHED. The defect was PRE-EXISTING rather than introduced alongside it,
#: and the sweep in `tests/test_no_secret_literals.py` restated the same
#: spelling, so there was no second line of defence over the tracked tree
#: either. That is why this is a CONSTANT the sweep imports rather than a
#: literal each side spells for itself.
#:
#: DERIVED BY SUBTRACTION over the ASCII universe, not by listing the shapes
#: somebody happened to probe. By the time `scan_for_leaks` runs the block is
#: known 7-bit ASCII - `extract_prompt` raises `non_ascii` first - so the
#: universe is the 128 codepoints. Removed, with the reason each:
#:
#:   - LETTERS AND DIGITS. A word character adjacent to the name means either
#:     the name is a prefix of a longer identifier, or an INTERVENING WORD has
#:     begun. THIS IS THE LINE AGAINST A PROXIMITY HEURISTIC. A class that
#:     admitted a word would fire on `<name> is <value>` prose, which is a
#:     different detector class with a different false-positive budget; it is
#:     recorded as out of scope in the sweep module rather than built here.
#:   - COMMA AND SEMICOLON, which close the current item.
#:   - DOT, SLASH AND BACKSLASH, which make the name part of a dotted
#:     expression or a path rather than a binding.
#:   - HASH, which begins a comment, so what follows is commentary.
#:   - PERCENT, DOLLAR, AMPERSAND, AT, BANG, CARET - value-side sigils. The
#:     percent and dollar forms are `ENV_REFERENCE`'s business and have to
#:     reach it WHOLE.
#:   - LEFT ANGLE, and this one was measured rather than reasoned. It opens an
#:     angle placeholder on the VALUE side; a separator that swallowed it would
#:     hand `ENV_REFERENCE`'s `<[^>]*>` a truncated value and turn every
#:     placeholder into a false positive. Right angle stays, for `->` and `=>`.
#:   - OPENING QUOTES AND BRACKETS after the operator, left to `VALUE_CAPTURE`,
#:     which owns the value's own quoting. A separator that ate the opening
#:     quote would hand the exemption a value it could no longer parse.
#:
#: THE OPERATOR IS MANDATORY, and that is the whole difference between this and
#: a proximity rule. Decoration and a gap are not a binding on their own: the
#: run has to CONTAIN one of the four glyphs that express a directed binding in
#: the syntaxes a hand-off block actually carries - colon (YAML, JSON, markdown,
#: a prose label), equals (shell, make, ini, Python), pipe (a markdown table
#: cell), right angle (`->` and `=>`). `?=`, `+=`, `:=` and `-` are legal
#: COMPANIONS in that run and none of them is sufficient alone.
_NAME_DECOR = r"""[ \t"'`*~_\]})]"""
_BIND_OPERATOR = r"[:=|>?+-]"
_BIND_CORE = r"[:=|>]"

#: THE WIDENING IS A STRICT SUPERSET, and the second alternative is how that
#: claim is checkable rather than asserted. The shape being replaced is kept
#: VERBATIM, so no detection it made can be lost by this change - including the
#: one the first alternative deliberately gives up, a binding whose value sits
#: on the NEXT LINE. The first alternative's gap is `[ \t]` and not `\s` on
#: purpose: line-bounded, it cannot walk from a markdown table cell across a
#: line break into the separator row below it and call the leading `|` a value.
#: That false positive was measured while deriving this. The legacy alternative
#: crosses lines only behind a literal `[:=]`, which is where it already was.
NAME_VALUE_SEPARATOR = (
    "(?:"
    + _NAME_DECOR
    + "*"
    + _BIND_OPERATOR
    + "*"
    + _BIND_CORE
    + _BIND_OPERATOR
    + r"*[ \t]*"
    + "|"
    + r"\"?\s*[:=]\s*"
    + ")"
)


def is_env_reference(value: str) -> bool:
    """True when a bound value is a LOOKUP rather than a literal.

    The two halves are separate because they are anchored differently, and
    collapsing them is how the exemption starts swallowing real literals.
    """
    if ENV_REFERENCE.search(value):
        return True
    return VARIABLE_VALUE.match(value.strip("\"'")) is not None

#: An absolute path under a Windows user profile, in the three spellings this
#: box actually produces: native, MSYS/Git-Bash, and WSL. `<account>` and other
#: angle-bracket placeholders are legal - the hand-off is allowed to SHOW the
#: shape it is refusing.
#: ASSEMBLED FROM PARTS, and that is not style. Written as one literal, this
#: pattern's own source is an account-shaped path, so
#: `tests/test_machine_identity.py` sweeps it up, and the only remedies then
#: are to allowlist a regex fragment or to loosen that guard. Both are worse
#: than a constant: an allowlist entry spelled as a chunk of regex is
#: unreadable and goes unstable the moment this line is edited, and loosening
#: the sweep is how it stops catching a real account. Naming the segment
#: removes the collision instead of negotiating with it.
_USERS = "Users"
ACCOUNT_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/]" + _USERS + r"[\\/]"
    r"|/c/" + _USERS + r"/"
    r"|/mnt/c/" + _USERS + r"/)"
    r"(?P<who>[^\\/\s\"']+)",
    re.IGNORECASE,
)

class Refusal(Exception):
    """A refusal of the hand-off, carrying a machine-readable reason."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def extract_prompt(source_text: str) -> str:
    """Return the hand-off text of `source_text`, or refuse.

    THE WHOLE FILE IS THE HAND-OFF, and that is a change of contract made on
    2026-09-19 when `NEXT_SESSION_PROMPT.md` became `RSC-NEXT-SESSION.txt`.
    The old source was a markdown page wrapping the hand-off in one fenced
    block, so this function's job was to find that block and refuse if the page
    carried zero or several. The new source is the RAW hand-off with no wrapper
    and no fence - which is what the sibling trees keep, and what the operator
    actually reads when the file is opened in Notepad. A
    wrapper and a pair of fences are noise in that window.

    A FENCED SOURCE IS STILL ACCEPTED AND STILL UNWRAPPED, deliberately. The
    fleet keeps five copies of this pattern and they will not migrate on the
    same day; refusing a fenced file would turn a shared tool into a local one.
    A file carrying MORE than one fenced block is still refused, because that
    file is ambiguous about which block is the hand-off and a guess there
    publishes the wrong text.

    Every other guard is UNCHANGED and now covers strictly more: the minimum
    size, the ASCII rule and the leak scan used to see one block of the source
    and now see all of it.
    """
    lines = source_text.splitlines(keepends=True)
    fences = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == FENCE]

    if len(fences) > 2:
        raise Refusal(
            "multiple_prompt_blocks",
            f"the source has {len(fences) // 2} fenced blocks; "
            "the hand-off must be the only one",
        )

    block = "".join(lines[fences[0] + 1 : fences[1]]) if len(fences) == 2 else source_text

    size = len(block.encode("ascii", errors="replace"))
    if size < MIN_BYTES:
        raise Refusal(
            "prompt_too_short",
            f"the block is {size} bytes, under the {MIN_BYTES}-byte floor - a "
            "truncated hand-off reads as current and is worse than a stale one",
        )

    offenders = sorted({ch for ch in block if ord(ch) > 127})
    if offenders:
        raise Refusal(
            "non_ascii",
            "the block carries non-ASCII characters "
            + ", ".join(f"U+{ord(ch):04X}" for ch in offenders),
        )

    for leak in scan_for_leaks(block):
        raise Refusal(*leak)

    return block


def scan_for_leaks(block: str) -> list[tuple[str, str]]:
    """`(reason, detail)` for every credential or account path in `block`.

    A LIST rather than a raise, so the arms that prove this has teeth can call
    it directly on a planted string without building a whole hand-off, and so a
    caller can report every offender rather than only the first.

    THE DETAIL NEVER ECHOES THE SECRET. It names the prefix or the variable and
    stops. A refusal message is printed to a terminal and pasted into notes, so
    a gate that quoted the key it caught would publish it in the act of
    refusing to publish it.

    THE CHARACTER COUNT IS A MATCH SPAN AND IS LABELLED AS ONE. There is no
    right boundary: the body class carries the vendor's own separators, so the
    greedy run walks off the end of the credential and into any prose glued on
    by a hyphen or an underscore. Measured - a 34-character GitHub-shaped token
    followed by `-secret_literal_notes` spans 55. A right lookahead was tried
    and REJECTED because it loses detections rather than shortening spans: with
    `(?![A-Za-z0-9_\\-])` appended, `xoxb-` plus sixteen digits plus `_tail`
    stops matching at all, since `_` is outside Slack's body class but inside
    the lookahead's. Two of three probes lost. So the span stays and the wording
    carries its own caveat.
    """
    found: list[tuple[str, str]] = []

    for vendor in VENDOR_TOKENS:
        for match in re.finditer(vendor.pattern(), block):
            found.append(
                (
                    "secret_literal",
                    f"the block carries what looks like a live credential "
                    f"(prefix {vendor.prefix!r}, match spans {len(match.group(0))} "
                    "chars - an UPPER BOUND on the token, since the span runs to "
                    "the end of the vendor's own alphabet and adjoining text can "
                    "be glued to it). Move it to a machine environment variable "
                    "and reference it by name.",
                )
            )

    for name in SECRET_NAMES:
        for match in re.finditer(
            re.escape(name) + NAME_VALUE_SEPARATOR + r"(?P<v>" + VALUE_CAPTURE + r")",
            block,
        ):
            value = match.group("v")
            # An environment REFERENCE is the destination of the rule, not a
            # violation of it. `${NAME}`, `%NAME%`, `$env:NAME`, `os.environ[...]`
            # and an angle-bracket placeholder all stay legal.
            if is_env_reference(value):
                continue
            found.append(
                (
                    "secret_literal",
                    f"the block binds {name} to a literal value. Reference the "
                    "machine environment variable instead.",
                )
            )

    for match in ACCOUNT_PATH.finditer(block):
        who = match.group("who")
        if who.startswith("<") or who.upper() in {"PUBLIC", "DEFAULT", "ALL USERS"}:
            continue
        # THE DETAIL NEVER ECHOES THE PATH, and this is the same rule the
        # credential branch above already followed. Until 2026-09-20 this line
        # interpolated `match.group(0)`, so a refusal PRINTED the real
        # `<drive>:\Users\<account>\...` prefix it had just refused to publish -
        # to a console, into a session transcript, and into whatever note the
        # refusal was pasted in. A gate that quotes the identifier it caught
        # publishes it in the act of refusing to publish it. Only the OFFSET is
        # reported, which is enough to find the line and carries nothing.
        found.append(
            (
                "account_path",
                "the block names a real user profile in an absolute path "
                f"(one match at character offset {match.start()}; the path is "
                "deliberately not echoed here). The hand-off is pasted into "
                "cold sessions and quoted into sibling repos, and this tree is "
                "public - use <account> instead.",
            )
        )

    return found

SESSION_COUNTER = (
    "the hand-off has no single readable column-0 SESSION: <n> line, so the "
    "next /done would write a guess plus one. Restore exactly one such line."
)
UNREADABLE = "the hand-off file could not be read as UTF-8 text"


def check_text(source_text: str) -> dict:
    """Every content rule over `source_text`, in order, or a `Refusal`.

    The block rules run first, so a truncated file is refused for its size
    whatever its counter says. The counter is read from the WHOLE source, not
    from a fenced block, because that is where `/done` and the SessionStart
    hook read it.
    """
    block = extract_prompt(source_text)
    number = session_number(source_text)
    if number is None:
        raise Refusal("session_counter", SESSION_COUNTER)
    return {"ok": True, "bytes": len(block.encode("ascii")), "session": number}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate the next-session hand-off's content. Reads, never writes."
    )
    parser.add_argument(
        "path", nargs="?", type=Path, default=None, help="file to gate (default: the hand-off)"
    )
    args = parser.parse_args(argv)
    path = args.path or SOURCE

    try:
        source_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        print(f"check_handoff: REFUSED unreadable - {UNREADABLE} ({path.name})")
        return 1

    try:
        report = check_text(source_text)
    except Refusal as refusal:
        print(f"check_handoff: REFUSED {refusal.reason} - {refusal.detail}")
        return 1

    print(
        f"check_handoff: ok - {path.name}, {report['bytes']} bytes, "
        f"SESSION {report['session']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
