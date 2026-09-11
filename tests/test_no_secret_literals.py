"""No tracked file may carry an API key or token as a literal.

THE RULE, operator instruction 2026-09-06: every API key on this machine lives
in a MACHINE-level environment variable, and no repository in the fleet carries
one inline. This guard is the half that keeps it true after the sweep.

WHY A NAIVE "LONG RANDOM STRING" RULE IS THE WRONG SHAPE, and it is the first
thing anyone writes. This tree is FULL of long high-entropy literals that are
entirely legitimate:

  - `tests/test_loop_concurrency.py` pins two sha256 digests of the shared
    governor files, 64 hex characters each. Those pins are the whole mechanism
    by which three repositories prove they carry identical bytes.
  - `tests/test_session_hooks.py` pins `BANNER_SHA256`, another 64 hex
    characters, for the same reason.
  - `shell/` embeds the tray icon as a base64 data URL.

A guard that flagged those would be deleted within a day, and deleting a guard
is how the property stops being checked. So this sweeps for the two shapes that
are ACTUALLY diagnostic of a secret and are never diagnostic of a digest:

  1. A VENDOR-PREFIXED TOKEN. Real credentials from these services carry a fixed
     prefix that a hash never has - `sk-`, `ghp_`, `github_pat_`, `AIza`,
     `RGAPI-`, `xox[bapsr]-`, `sk-ant-`.
  2. A KNOWN SECRET VARIABLE NAME BOUND TO A LITERAL. `NIMBLE_API_KEY = "..."`,
     `"ANTHROPIC_API_KEY": "..."`, `GITHUB_PERSONAL_ACCESS_TOKEN=...`. The
     variable name is the evidence; the value's entropy is irrelevant. This is
     the arm that would have caught the real finding, which sat in an `env`
     block under exactly that name.

Binding one of these names to an ENV LOOKUP is the correct pattern and must
stay legal: `os.environ["NIMBLE_API_KEY"]`, `${NIMBLE_API_KEY}`,
`%NIMBLE_API_KEY%`, `$env:NIMBLE_API_KEY`. The point of the rule is to move
secrets to the environment, so the guard must not punish the destination.

TRACKEDNESS, NOT PRESENCE. The corpus comes from `git ls-files`, not a disk
walk. A disk walk sweeps a contributor's `.venv/` and anything else gitignored,
which is not what "this repository carries a secret" means - and it is the
defect this tree already fixed in `tests/test_ports.py`.

NON-VACUITY IS ASSERTED, NOT ASSUMED. A sweep that selects nothing reports zero
offenders out of zero files and is indistinguishable from a clean tree. Every
arm below asserts the SCANNED COUNT first. The mutation arms drive the detector
with planted strings so its teeth are proven independently of whether the tree
happens to be clean today.

TWO GUARDS, NOT ONE. One arm says a planted secret IS caught; its partner says
the legitimate neighbours - the sha256 pins, the base64 icon, the env lookups -
SURVIVE. A detector that flagged everything would pass the first arm of every
pair while telling the reader nothing true.
"""
from __future__ import annotations

import re
import string
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

from tests.conftest import require_git_repository
from tools import publish_next_session as pns

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Vendor prefixes that identify a real credential. A sha256 digest, a git SHA
#: and a base64 blob never carry one, which is what makes these safe to sweep.
#:
#: IMPORTED, NOT RESTATED. The copy that used to sit here and the publisher's
#: `SECRET_PREFIXES` tuple were the last surviving pair, and they had already
#: drifted in EIGHT cases with every arm green - three of which leaked through
#: the real publish path. See the single-source section at the foot of this
#: module, and `VENDOR_TOKENS` in `tools/publish_next_session.py` for how the
#: unified length rule was derived.
VENDOR_TOKEN = pns.VENDOR_TOKEN

#: The secret-bearing variable names in use on this machine, 2026-09-06. Held
#: as a literal set rather than read from the environment: a guard that asked
#: the live environment would go SILENT on a machine where the variables are
#: not set, which is every CI runner and every fresh clone.
#:
#: IMPORTED, NOT RESTATED. See the single-source section at the foot of this
#: module for why the copy that used to sit here was deleted rather than
#: paired with a drift detector.
SECRET_NAMES = pns.SECRET_NAMES

#: `NAME = "value"` / `"NAME": "value"` / `NAME=value`, where value is a bare
#: literal of any length. Length is deliberately NOT part of the test: a short
#: value bound to one of these names is either a secret or a placeholder, and a
#: placeholder should be an env reference too.
#:
#: The VALUE half is imported too. It has to be: the exemption below decides
#: whether a captured value is a lookup, so a capture that truncates and an
#: exemption that expects the whole thing disagree silently, which is exactly
#: what `pns.VALUE_CAPTURE` was extracted to stop.
#:
#: AND SO IS THE SEPARATOR, for the same reason and on measured evidence. The
#: spelling that used to sit here restated the publisher's, so it inherited
#: every one of that spelling's misses and there was no second line of defence
#: over the tracked tree at all. A backtick-wrapped name, a bold name, a
#: markdown table row, a single-quoted key, `?=`, `+=` and `->` were all missed
#: by BOTH, identically. One object cannot drift from itself. See
#: `NAME_VALUE_SEPARATOR` in `tools/publish_next_session.py` for how its
#: character population was derived, and the section at the foot of this module
#: for what is deliberately still out of its scope.
SECRET_BINDING = re.compile(
    r"(?:" + "|".join(SECRET_NAMES) + r")"
    + pns.NAME_VALUE_SEPARATOR
    + r"(?P<value>" + pns.VALUE_CAPTURE + r")"
)

#: Referencing the environment is the CORRECT pattern and stays legal. Anything
#: matching one of these as the bound value is a lookup, not a literal.
ENV_REFERENCE = pns.ENV_REFERENCE

#: A bound value that IS a variable reference in its ENTIRETY - PowerShell or
#: shell `$key` - is a lookup rather than a literal.
#:
#: Anchored deliberately, and kept OUT of `ENV_REFERENCE`. That pattern is
#: applied with `.search()`, so folding a bare `$name` into it would exempt any
#: value merely CONTAINING one, and `"abc$key"` - a real literal with a variable
#: spliced in - would go quiet. The arms below hold both halves.
#:
#: Reported by Sibling-E on 2026-09-07 against its own ported copy:
#: `$env:GEMINI_API_KEY = $key` was flagged although `$key` had been read from
#: `GetEnvironmentVariable` on the line above. That is the CORRECT destination
#: and the guard called it a leak.
#:
#: "LATENT HERE RATHER THAN LIVE" WAS TRUE OF THIS MODULE AND FALSE OF THE TREE,
#: and the count beside it was wrong as well. Corrected 2026-09-11, both halves
#: measured: `git ls-files "*.ps1"` returns TWO paths, not one -
#: `ops/install_responder_task.ps1` and `ops/install_scheduled_task.ps1` - and
#: neither carries the shape (the one `$env:` read in either is
#: `$env:USERDOMAIN` in the scheduled-task installer, a read and not a binding).
#: The false positive was NOT latent in the tree: the same exemption list had
#: been copied into `tools/publish_next_session.py`, that copy never got this
#: fix, and it refused a real hand-off on the publish path. See the
#: single-source section at the foot of this module.
VARIABLE_VALUE = pns.VARIABLE_VALUE

#: Files whose JOB is to carry these patterns. Exempt BY NAME so the exemption
#: stays a short visible list rather than a rule that quietly widens.
#:
#: Both entries plant fake credentials DELIBERATELY, as the fixtures that prove
#: their own detectors have teeth. Exempting them is not a hole: the arm below
#: asserts each one would actually TRIP the sweep, so an exemption that stopped
#: being load-bearing is reported rather than left standing.
SELF_EXEMPT = {
    "tests/test_no_secret_literals.py",
    "tests/test_publish_next_session.py",
}


@lru_cache(maxsize=1)
def _tracked_text_files() -> tuple[str, ...]:
    """Every tracked file git will show us, asked of GIT rather than the disk."""
    require_git_repository()
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return tuple(sorted(p for p in out.split("\0") if p))


def scan_text(text: str) -> list[str]:
    """Offending fragments in `text`. Pure, so the mutation arms can drive it."""
    hits: list[str] = []
    for match in VENDOR_TOKEN.finditer(text):
        hits.append(f"vendor-prefixed token: {match.group(0)[:12]}...")
    for match in SECRET_BINDING.finditer(text):
        value = match.group("value")
        # The two exemption halves are anchored differently and are applied by
        # the publisher's own helper, so the sweep and the hand-off gate cannot
        # answer this question differently. They used to.
        if pns.is_env_reference(value):
            continue
        hits.append(f"secret name bound to a literal: {match.group(0)[:48]}")
    return hits


def sweep() -> tuple[int, list[str]]:
    """`(files_scanned, offenders)`. The COUNT is returned so arms can assert it."""
    scanned = 0
    offenders: list[str] = []
    for rel in _tracked_text_files():
        if rel in SELF_EXEMPT:
            continue
        path = REPO_ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scanned += 1
        for hit in scan_text(text):
            offenders.append(f"{rel}: {hit}")
    return scanned, offenders


# ---------------------------------------------------------------------------
# The sweep over the real tree
# ---------------------------------------------------------------------------


def test_the_sweep_selects_a_real_corpus():
    """Non-vacuity, asserted BEFORE any cleanliness claim is made."""
    scanned, _ = sweep()
    assert scanned > 100, (
        f"the secret sweep scanned only {scanned} tracked files. It is supposed "
        "to cover the whole repository; a short list reports zero offenders out "
        "of almost nothing and reads exactly like a clean tree."
    )


def test_no_tracked_file_carries_a_secret_literal():
    scanned, offenders = sweep()
    assert offenders == [], (
        f"{len(offenders)} secret literal(s) in tracked files, out of {scanned} "
        "scanned. Every API key belongs in a machine environment variable "
        "(operator instruction 2026-09-06); reference it as os.environ[...] or "
        "${NAME} instead:\n  " + "\n  ".join(offenders)
    )


# ---------------------------------------------------------------------------
# The detector has teeth - planted strings, nothing on disk touched
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "planted",
    [
        'NIMBLE_API_KEY = "0123456789abcdef0123456789abcdef"',
        '"ANTHROPIC_API_KEY": "sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAA"',
        "GITHUB_PERSONAL_ACCESS_TOKEN=ghp_" + "A" * 36,
        "token = 'sk-" + "B" * 32 + "'",
        "key = 'AIza" + "C" * 35 + "'",
        "riot = 'RGAPI-" + "0" * 8 + "-" + "1" * 4 + "-" + "2" * 24 + "'",
        "slack = 'xoxb-" + "9" * 24 + "'",
    ],
)
def test_a_planted_secret_is_caught(planted):
    assert scan_text(planted), f"the detector missed a planted secret: {planted[:40]}"


@pytest.mark.parametrize(
    "innocent",
    [
        # The governor pins and the banner pin. 64 hex characters each, and the
        # single most important thing this guard must NOT flag.
        '"slots.py": "629c3d511d2500f92d25fbe102a7a8c73644c027291f46b8796565a1e839f865"',
        'BANNER_SHA256 = "b527af9597a3f1d3f7a853854dcd0cb6c6b616977deb60101a06da43906df535"',
        # A git SHA and a base64 blob.
        "commit 7fbda4ad8abb783797af93b73919022685c1bb45",
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAAB",
        # The CORRECT pattern: the name bound to an environment lookup.
        'key = os.environ["NIMBLE_API_KEY"]',
        'NIMBLE_API_KEY: "${NIMBLE_API_KEY}"',
        "ANTHROPIC_API_KEY=%ANTHROPIC_API_KEY%",
        '$k = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY")',
        'NIMBLE_API_KEY: "MOVED-TO-USER-ENV-VAR-NIMBLE_API_KEY"',
        # Prose naming the variable without binding it.
        "Set NIMBLE_API_KEY in the machine environment before running.",
    ],
)
def test_a_legitimate_neighbour_survives(innocent):
    """The partner guard. A detector that flags everything proves nothing."""
    assert not scan_text(innocent), f"false positive on legitimate content: {innocent[:60]}"


def test_the_self_exemption_is_narrow_and_real():
    """This module names the patterns, so it is exempt - and only it is."""
    assert SELF_EXEMPT == {
        "tests/test_no_secret_literals.py",
        "tests/test_publish_next_session.py",
    }
    tracked = set(_tracked_text_files())
    for rel in SELF_EXEMPT:
        assert rel in tracked, (
            f"{rel} is exempted but is not tracked; a stale exemption silently "
            "widens the moment the file is renamed"
        )


def test_the_detector_would_fail_on_this_file_without_its_exemption():
    """Proves the exemption is load-bearing rather than decorative.

    If this module ever stops containing planted examples, the exemption is
    dead weight and should go. Asserting it here means the next reader is told
    which of the two is true rather than guessing.
    """
    for rel in sorted(SELF_EXEMPT):
        body = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert scan_text(body), (
            f"{rel} is exempted but no longer trips the detector, so its "
            "exemption is unnecessary - remove it rather than leaving a hole"
        )
    own = (REPO_ROOT / "tests" / "test_no_secret_literals.py").read_text(encoding="utf-8")
    assert scan_text(own), (
        "this module no longer trips its own detector, so SELF_EXEMPT is "
        "unnecessary - remove the exemption rather than leaving a hole"
    )


#: The PowerShell shape Sibling-E measured: a variable holding a value
#: already read from the environment, assigned to the env destination. Built
#: from `chr(36)` so this module's own text does not carry the literal binding
#: it is describing.
_DOLLAR = chr(36)
_WHOLE_VARIABLE = f"{_DOLLAR}env:GEMINI_API_KEY = {_DOLLAR}key"
_SPLICED_VARIABLE = f'GEMINI_API_KEY = "abc{_DOLLAR}key"'
_TRAILING_LITERAL = f'GEMINI_API_KEY={_DOLLAR}key"abc123"'


def test_a_value_that_is_wholly_a_variable_reference_is_a_lookup():
    """The false positive Sibling-E reported, closed - and the check is ARMED first.

    Asserting only that nothing was flagged would pass for a module whose
    binding pattern had stopped matching altogether, which is the vacuous-pass
    shape. So the arming assertion comes first: the binding must actually fire
    on this text before its absence from the offender list means anything.
    """
    armed = SECRET_BINDING.search(_WHOLE_VARIABLE)
    assert armed is not None, (
        "the binding pattern no longer matches the assignment shape, so this "
        "arm proves nothing about the variable-value exemption"
    )
    assert armed.group("value") == f"{_DOLLAR}key"
    assert scan_text(_WHOLE_VARIABLE) == [], (
        "a value that is entirely a variable reference is a lookup, not a "
        "literal, and flagging it teaches the reader to wave the guard through"
    )


def test_a_value_that_merely_contains_a_variable_is_still_a_literal():
    """Why the exemption is anchored rather than folded into ENV_REFERENCE.

    `ENV_REFERENCE` is applied with `.search()`. A bare `$name` added to it
    would exempt every value that merely CONTAINS one, and this line - a real
    literal with a variable spliced into it - would go quiet. The refusal and
    the acceptance above are the pair; without this one, an exemption that
    swallowed everything would still pass the test above.
    """
    armed = SECRET_BINDING.search(_SPLICED_VARIABLE)
    assert armed is not None, "the binding pattern did not fire, so this arm is vacuous"
    assert scan_text(_SPLICED_VARIABLE) != [], (
        "a literal with a variable spliced into it is still a literal; the "
        "variable-value exemption must stay anchored to the WHOLE value"
    )


def test_a_variable_followed_by_a_literal_is_still_a_literal():
    """The arm that makes the TRAILING anchor load-bearing.

    The leading anchor is redundant - `.match()` already anchors at the start -
    so a mutant that drops only `^` is EQUIVALENT and this pair would not catch
    it. The trailing anchor is the half that does work: without it the value
    below matches on its `$key` prefix, the appended literal is never looked at,
    and the secret rides out of the tree exempted. Measured as a false negative
    before this arm was written.
    """
    armed = SECRET_BINDING.search(_TRAILING_LITERAL)
    assert armed is not None, "the binding pattern did not fire, so this arm is vacuous"
    assert armed.group("value") == f'{_DOLLAR}key"abc123"', (
        "the value capture changed shape, so this arm no longer exercises a "
        "variable prefix followed by a literal"
    )
    assert scan_text(_TRAILING_LITERAL) != [], (
        "a variable prefix does not launder the literal appended to it; the "
        "exemption must match the value end to end"
    )


# ---------------------------------------------------------------------------
# ONE SOURCE, NOT TWO COPIES AND A DRIFT DETECTOR
# ---------------------------------------------------------------------------
#
# THE DEFECT. This module's exemption list and the one inside
# `tools/publish_next_session.py` were two independently hand-maintained copies
# with NOTHING between them, and they HAD ALREADY DRIFTED. Measured in-process
# 2026-09-11, before this section existed:
#
#     tools.publish_next_session.scan_for_leaks("$env:GEMINI_API_KEY = $key")
#       -> [("secret_literal", ...)]                       REFUSED
#     tests.test_no_secret_literals.scan_text("$env:GEMINI_API_KEY = $key")
#       -> []                                              exempt
#
# That exact false positive is documented as CLOSED at `VARIABLE_VALUE` above.
# It was closed in THIS COPY ONLY. The publisher went on refusing it, and
# `tests/test_publish_next_session.py` contained zero occurrences of `env:`, so
# nothing in the tree could see the disagreement.
#
# WHY A SINGLE SOURCE RATHER THAN A DRIFT DETECTOR BETWEEN TWO COPIES. A
# detector is the repair only when one source is genuinely impossible, and here
# it is not. The reason the copies existed is recorded in the publisher's own
# docstring and is a real constraint - a hand-off gate that imported from
# `tests/` would be a tool depending on tests to run - but it constrains the
# DIRECTION, not the count. The test importing the tool breaks nothing: the
# publisher still runs standalone with no test module on the path. So the
# patterns live in `tools/publish_next_session.py` and this module imports
# them. One object cannot drift from itself, and a detector would only have
# told us AFTER the next divergence what an import makes unrepresentable.
#
# WHAT WAS STILL TWO COPIES, and is not any more. That pass left the VENDOR
# PREFIXES paired and argued the pairing was unfixable: `VENDOR_TOKEN` here was
# one alternation with per-vendor length floors, `SECRET_PREFIXES` there was a
# tuple used with a single shared floor, so "they are not the same object in any
# sense that an import would fix". The premise was right and the conclusion was
# wrong, in the same way the exemption-list conclusion had been. Two shapes that
# answer ONE question are a reason to decide which shape is the contract, not a
# licence to keep both. The very next section measures what keeping both cost.


def test_the_exemption_is_one_object_shared_with_the_publisher():
    """Drift is unrepresentable, not merely detected.

    Identity, not equality. Two equal-but-separate patterns are exactly the
    state this replaced, and an equality arm would pass in that state.
    """
    assert ENV_REFERENCE is pns.ENV_REFERENCE
    assert VARIABLE_VALUE is pns.VARIABLE_VALUE
    assert SECRET_NAMES is pns.SECRET_NAMES


@pytest.mark.parametrize(
    "shared",
    [
        # BEHAVIOUR, not identity. The arm above would still pass if both sides
        # shared one BROKEN object, so these feed the inputs that drifted and
        # require the two entry points to agree on each of them.
        "$env:GEMINI_API_KEY = $key",
        "ANTHROPIC_API_KEY = $env:ANTHROPIC_API_KEY",
        'RIOT_API_KEY = [Environment]::GetEnvironmentVariable("RIOT_API_KEY")',
        "NIMBLE_API_KEY=%NIMBLE_API_KEY2%",
        "GEMINI_API_KEY=${gemini_api_key}",
        "RIOT_API_KEY=%PROGRAMFILES(X86)%",
    ],
)
def test_the_sweep_and_the_publisher_agree_that_a_reference_is_a_lookup(shared):
    assert scan_text(shared) == [], "the tracked-tree sweep refused a lookup: " + shared
    assert pns.scan_for_leaks(shared) == [], "the publisher refused a lookup: " + shared


@pytest.mark.parametrize(
    "literal",
    [
        # The partner guard for the pair above. Both entry points must still
        # refuse a real literal, or the shared exemption has swallowed the rule.
        'NIMBLE_API_KEY = "0123456789abcdef0123456789abcdef"',
        'GEMINI_API_KEY = "abc$key"',
        'RIOT_API_KEY = "${unterminated"',
    ],
)
def test_the_sweep_and_the_publisher_agree_that_a_literal_is_a_literal(literal):
    assert scan_text(literal) != [], "the tracked-tree sweep exempted a literal: " + literal
    assert pns.scan_for_leaks(literal) != [], "the publisher exempted a literal: " + literal


# ---------------------------------------------------------------------------
# THE VENDOR PREFIXES WERE THE REMAINING PAIR, AND THE PAIR HAD ALREADY DRIFTED
# ---------------------------------------------------------------------------
#
# THE DEFECT, measured end to end 2026-09-11 with NO mutation - the shipped
# bytes already disagreed, with every arm in the tree green. The section above
# recorded the vendor prefixes as a KNOWN remaining pair on the grounds that
# `VENDOR_TOKEN` here and `SECRET_PREFIXES` in the publisher were different
# SHAPES. Different shapes is a reason to pick one, not a reason to keep two:
#
#   caught by the SWEEP, missed by the PUBLISHER: xoxa- xoxs- xoxr-
#   caught by the PUBLISHER, missed by the SWEEP: ghp_ AIza RGAPI- github_pat_
#                                                 at 20 body chars, sk- at 16
#
# Three of those leaked through the real publish path. `xoxb-` was refused;
# `xoxa-` and `xoxs-` were PUBLISHED, ok=True, token on disk. The sweep runs
# over the COMMITTED tree. The publisher is the only gate on the path that
# LEAVES the toolchain, so a token the sweep catches and the publisher misses
# reaches the Desktop.
#
# WHICH SHAPE IS THE CONTRACT, decided by measurement rather than by taste. The
# publisher's shape - one wide class `[A-Za-z0-9_\-]` with one shared floor of
# 16 - is measurably wrong. Applied to the union of both prefix lists over the
# 221 readable tracked files it produces NINE false positives, every one of
# them a hyphen-segmented test identifier where `sk-` is the tail of `task-`:
# `task-argv-does-not-arm`, `task-argv-is-a-dry-run`,
# `task-name-argument-is-dropped`. Raising that shared floor to 20 still leaves
# one. So the per-vendor character class the sweep carried is load-bearing and
# the publisher's flat tuple had thrown it away.
#
# THE UNIFIED RULE, and it is neither list's rule. See `MIN_BODY` and
# `LEFT_BOUNDARY` in `tools/publish_next_session.py` for the derivation and for
# the measured regression that replaced the first attempt at it; both detectors
# are built from that one table and this module imports the compiled result.
# The section at the foot of THIS module is where that regression is recorded
# from the sweep's side.
#
# THE ROSTER BELOW IS THE ANCHOR, hand-written and never imported from the
# tool. An arm that iterated the tool's own table would be checking the list
# against itself and would stay green when a prefix was deleted from it.

#: Every vendor prefix the two detectors named between them, HAND COUNTED by
#: vendor: five Slack spellings, two OpenAI/Anthropic, two GitHub, one Google,
#: one Riot. Eleven.
_SLACK_PREFIXES = ("xoxa-", "xoxb-", "xoxp-", "xoxr-", "xoxs-")
_OPENAI_PREFIXES = ("sk-ant-", "sk-")
_GITHUB_PREFIXES = ("ghp_", "github_pat_")
_GOOGLE_PREFIXES = ("AIza",)
_RIOT_PREFIXES = ("RGAPI-",)
VENDOR_PREFIX_ROSTER = (
    _SLACK_PREFIXES + _OPENAI_PREFIXES + _GITHUB_PREFIXES + _GOOGLE_PREFIXES + _RIOT_PREFIXES
)

#: SYNTHETIC, and deliberately not credential-shaped beyond its length: forty
#: repeated zeros. Every vendor's character class accepts a digit, so one body
#: drives all eleven prefixes. Nothing in this file is or resembles a live key.
SYNTHETIC_BODY = "0" * 40


def test_the_vendor_roster_buckets_sum_to_a_hand_counted_population():
    """A floor. An emptied population parametrizes to nothing and SKIPS at rc 0."""
    buckets = (
        _SLACK_PREFIXES,
        _OPENAI_PREFIXES,
        _GITHUB_PREFIXES,
        _GOOGLE_PREFIXES,
        _RIOT_PREFIXES,
    )
    assert sum(len(bucket) for bucket in buckets) == 11
    assert len(VENDOR_PREFIX_ROSTER) == 11
    assert len(set(VENDOR_PREFIX_ROSTER)) == 11, "a prefix is rostered twice"


@pytest.mark.parametrize("prefix", VENDOR_PREFIX_ROSTER)
def test_the_sweep_and_the_publisher_agree_on_every_vendor_prefix(prefix):
    """Driven as INPUT through both entry points. Not a claim about a spelling.

    This is the arm the drift defeated: at HEAD the publisher answered `[]` for
    `xoxa-`, `xoxs-` and `xoxr-` while the sweep flagged them, and answered
    `secret_literal` for five prefixes at body lengths the sweep waved through.
    """
    token = "token " + prefix + SYNTHETIC_BODY
    assert scan_text(token) != [], "the tracked-tree sweep missed prefix " + prefix
    assert pns.scan_for_leaks(token) != [], "THE PUBLISHER missed prefix " + prefix


def test_no_vendor_prefix_is_rostered_that_the_single_source_has_dropped():
    """Conservation on the prefix list, anchored outside the list itself."""
    table = {entry.prefix for entry in pns.VENDOR_TOKENS}
    missing = sorted(set(VENDOR_PREFIX_ROSTER) - table)
    assert missing == [], (
        "vendor prefix(es) dropped from tools/publish_next_session.py without "
        "the roster moving: " + ", ".join(missing) + ". Both detectors are "
        "built from that table, so a deletion there blinds BOTH of them."
    )
    extra = sorted(table - set(VENDOR_PREFIX_ROSTER))
    assert extra == [], (
        "vendor prefix(es) added to the single source but not reviewed here: "
        + ", ".join(extra)
    )


#: SYNTHETIC, in Riot's 8-4-4-4-12 layout, every group a single repeated digit.
#: Not a key and not derived from one; the SHAPE is the whole point of it.
SYNTHETIC_SEGMENTED_BODY = "0" * 8 + "-" + "1" * 4 + "-" + "2" * 4 + "-" + "3" * 4 + "-" + "4" * 12


def test_a_segmented_riot_key_is_caught_by_both():
    """Riot's real format is segmented, and this arm is why that was noticed.

    HISTORY, because the arm outlived the rule it was written against.
    2026-09-11 the unified rule counted an UNBROKEN RUN of 16, and Riot is the
    one vendor whose real format is itself segmented - 8-4-4-4-12, longest run
    TWELVE - so it was missed while BOTH old detectors caught it. That was
    answered with a per-vendor patch to Riot's own row, and the patch is what
    hid the fact that the RULE was wrong for all eleven vendors. The rule is a
    LEFT BOUNDARY now, Riot's row is shaped like every other row, and this arm
    keeps doing the job it was written for: proving the segmented case is
    caught, not proving any particular spelling of the rule.
    """
    token = "riot " + "RGAPI-" + SYNTHETIC_SEGMENTED_BODY
    assert max(len(part) for part in SYNTHETIC_SEGMENTED_BODY.split("-")) < 16, (
        "the fixture no longer has a sub-16 longest run, so it no longer "
        "exercises the segmented case at all"
    )
    assert scan_text(token) != [], "the tracked-tree sweep missed a segmented Riot key"
    assert pns.scan_for_leaks(token) != [], "THE PUBLISHER missed a segmented Riot key"


def test_the_vendor_matcher_is_one_object_shared_with_the_publisher():
    """Identity, not equality - two equal patterns is the state this replaced.

    `re.compile` returns the SAME object for an identical pattern string out of
    its internal cache, so an identity arm can pass against two independently
    compiled copies. That is why the behaviour arm above exists and why this one
    is the weaker of the pair rather than the proof.
    """
    assert VENDOR_TOKEN is pns.VENDOR_TOKEN


# ---------------------------------------------------------------------------
# THE NAME LIST NEEDS A CONSERVATION ASSERTION, NOT A SELF-CHECK
# ---------------------------------------------------------------------------
#
# THE DEFECT, measured 2026-09-11. `ANTHROPIC_USAGE_KEY` occurred in exactly ONE
# tracked file of 223 - `tools/publish_next_session.py` - and in ZERO test
# files. Deleting that one 27-byte line left the suite green:
#
#     BASELINE  python -m pytest tests  ->  rc 0, 2309 passed 1 skipped
#     MUTANT    python -m pytest tests  ->  rc 0, 2309 passed 1 skipped
#
# and the mutation is genuinely wrong: a binding of that name to a literal goes
# from caught by BOTH detectors to caught by NEITHER.
#
# THE CONSOLIDATION DOUBLED THE BLAST RADIUS, and that is the part worth
# carrying forward rather than the individual name. Before the single-source
# change this module held its own copy of the list, so the identical edit
# disabled ONE detector and the other still fired. Afterwards it disables both.
# Removing a duplicate removes the redundancy that was accidentally covering it,
# so a single source OWES its list a conservation arm.
#
# THE ANCHOR. An arm that imports `pns.SECRET_NAMES` and checks it against
# itself cannot see a deletion: the list and the expectation move together.
# The roster below is HAND-WRITTEN here, bucketed by vendor so the buckets sum
# to a hand-counted population, and nothing but these arms reads it - so it is
# an expectation rather than a second detector that could drift into disagreeing
# with the first.

_ANTHROPIC_NAMES = ("ANTHROPIC_API_KEY", "ANTHROPIC_USAGE_KEY")
_NIMBLE_NAMES = ("NIMBLE_API_KEY",)
_GEMINI_NAMES = ("GEMINI_API_KEY",)
_RIOT_NAMES = ("RIOT_API_KEY",)
_GITHUB_NAMES = ("GITHUB_PERSONAL_ACCESS_TOKEN",)
SECRET_NAME_ROSTER = (
    _ANTHROPIC_NAMES + _NIMBLE_NAMES + _GEMINI_NAMES + _RIOT_NAMES + _GITHUB_NAMES
)

#: SYNTHETIC. Thirty-two hex characters that spell out the digits in order, so
#: the reader can see at a glance that it is a dummy and not a redaction.
SYNTHETIC_VALUE = "0123456789abcdef" * 2


def test_the_name_roster_buckets_sum_to_a_hand_counted_population():
    """The floor. Emptying the roster must not read as a pass."""
    buckets = (
        _ANTHROPIC_NAMES,
        _NIMBLE_NAMES,
        _GEMINI_NAMES,
        _RIOT_NAMES,
        _GITHUB_NAMES,
    )
    assert sum(len(bucket) for bucket in buckets) == 6
    assert len(SECRET_NAME_ROSTER) == 6
    assert len(set(SECRET_NAME_ROSTER)) == 6, "a name is rostered twice"


def test_no_secret_name_may_be_dropped_from_the_single_source():
    """The conservation assertion. This is the arm the deletion defeated."""
    missing = sorted(set(SECRET_NAME_ROSTER) - set(pns.SECRET_NAMES))
    assert missing == [], (
        "secret variable name(s) dropped from tools/publish_next_session.py: "
        + ", ".join(missing)
        + ". That list is the single source for BOTH detectors, so a deletion "
        "there blinds the tracked-tree sweep AND the publish gate at once."
    )
    extra = sorted(set(pns.SECRET_NAMES) - set(SECRET_NAME_ROSTER))
    assert extra == [], (
        "secret variable name(s) added to the single source but not reviewed "
        "here: " + ", ".join(extra)
    )


@pytest.mark.parametrize("name", SECRET_NAME_ROSTER)
def test_every_rostered_name_bound_to_a_literal_is_caught_by_both(name):
    """Behaviour, driven from the anchor rather than from the list under test."""
    planted = name + ' = "' + SYNTHETIC_VALUE + '"'
    assert scan_text(planted) != [], "the tracked-tree sweep missed " + name
    assert pns.scan_for_leaks(planted) != [], "THE PUBLISHER missed " + name


def test_a_name_outside_the_roster_is_not_treated_as_a_secret():
    """The partner guard. A detector that flags every binding proves nothing."""
    planted = 'RESIN_DATA_DIR = "' + SYNTHETIC_VALUE + '"'
    assert scan_text(planted) == [], "the sweep flagged an ordinary binding"
    assert pns.scan_for_leaks(planted) == [], "the publisher flagged an ordinary binding"


# ---------------------------------------------------------------------------
# THE DISCRIMINATOR IS A TOKEN BOUNDARY, NOT CONTIGUITY
# ---------------------------------------------------------------------------
#
# THE REGRESSION THE CONTIGUITY RULE INTRODUCED, measured in-process 2026-09-11
# against the shipped bytes, driving both entry points directly:
#
#     probe  xoxb- + 13 ones + "-" + 13 twos + "-" + 24 capitals   (SYNTHETIC)
#     scan_text(...)        -> []          MISSED
#     scan_for_leaks(...)   -> []          MISSED
#     the OLD sweep and the OLD publisher  -> BOTH caught it
#
# `xoxb-` was never leaking before. Closing `xoxa-`/`xoxr-`/`xoxs-` at the FLAT
# body shape opened every SEGMENTED shape of all five Slack spellings.
#
# THE MECHANISM IS THE LEAD-IN BOUND, NOT THE RUN. In that probe the final run
# is 24 characters - fully intact, 8 over the 16-character floor. What kills it
# is `MAX_LEAD`: the identifier segments ahead of the run measured 28
# characters, four over the bound, so the matcher could not stride from the
# prefix to the run. A credential whose secret is UNTOUCHED was missed solely
# because its identifier segments were two characters too long.
#
# SCALE, re-derived here by a DECLARED METHOD rather than by listing cases: the
# full cartesian product of the eleven rostered vendor prefixes and the four
# segmentation layouts below, 44 tokens. THIRTY of the 44 were caught by an old
# detector and missed by BOTH new ones.
#
# WHY THE RULE WAS WRONG RATHER THAN UNDER-PATCHED. The builder met this exact
# defect class for ONE vendor - `test_a_segmented_riot_key_is_caught_by_both`
# above - and answered it by widening Riot's own `core`. There was no Slack,
# Anthropic or Google sibling of that arm, so ten vendors kept the defect. A
# per-vendor patch to a rule that is wrong for every vendor is the shape of the
# mistake, not the repair.
#
# THE DISCRIMINATOR, DERIVED FROM THE NINE FALSE POSITIVES rather than assumed.
# The contiguity rule was invented to solve a real problem: the old publisher's
# wide class at a flat floor of 16, applied to all eleven prefixes, produced
# NINE hits over the 221 readable tracked files at HEAD. Re-derived this run:
#
#     flat wide class, floor 16   ->  9 hits   (3 in tests/test_responder_task_argv.py,
#                                               6 in tests/test_supervisor_task_argv.py)
#     flat wide class, floor 20   ->  1 hit
#     flat wide class, floor 16, LEFT BOUNDARY  ->  0 hits
#
# What all nine share is not their length and not their segmentation. It is
# that the match DOES NOT START AT A TOKEN BOUNDARY: in every one of them `sk-`
# is the tail of the English word `task-`, so the character before the match is
# a letter. Three distinct identifiers account for all nine occurrences, and
# they are rostered below by hand.
#
# So the rule is: a credential match must begin where a token begins. That
# costs nothing on the LENGTH axis and nothing on the SEGMENTATION axis - the
# vendor's own separators stay inside its body class, exactly as this tree's own
# prior spec had them at `git show HEAD:tests/test_no_secret_literals.py`, which
# spelled Slack as `xox[bapsr]-[A-Za-z0-9\-]{20,}` with the hyphen INSIDE the
# body. The contiguity rule contradicted a spec the tree already carried.

#: The adversary's exact probe token. SYNTHETIC - repeated characters, not
#: derived from any key. Built from parts so the reader can count the segments.
ADVERSARY_PROBE = "xoxb-" + "1" * 13 + "-" + "2" * 13 + "-" + "C" * 24

#: Four segmentation layouts, all bodies built from REPEATED DIGITS so one body
#: drives every vendor: a digit is in every vendor's alphabet in the table,
#: including Riot's hex-only one. SYNTHETIC throughout.
#:
#:   FLAT        one unbroken run of 40 - the only shape the old fixtures used,
#:               which is why a flat-body probe set saw nothing wrong.
#:   SEGMENTED13 the adversary's shape - 28 characters of lead-in, run 24.
#:   SEGMENTED10 uniform 10-character groups - longest run 10, under any floor.
#:   RIOT_LAYOUT Riot's real 8-4-4-4-12 - longest run 12, from this tree's own
#:               fixture rather than from memory.
SEGMENTATION_LAYOUTS = {
    "FLAT": "0" * 40,
    "SEGMENTED13": "1" * 13 + "-" + "2" * 13 + "-" + "3" * 24,
    "SEGMENTED10": "-".join(str(digit) * 10 for digit in range(1, 6)),
    "RIOT_LAYOUT": SYNTHETIC_SEGMENTED_BODY,
}

#: The probe population: every rostered prefix against every layout. Declared as
#: a product rather than enumerated, so adding a vendor to the roster adds four
#: probes and cannot be forgotten.
VENDOR_LAYOUT_PROBES = tuple(
    (prefix, layout, prefix + body)
    for prefix in VENDOR_PREFIX_ROSTER
    for layout, body in SEGMENTATION_LAYOUTS.items()
)


def test_the_probe_set_is_the_declared_product_and_is_not_empty():
    """The floor. An emptied parametrize is `1 skipped` at exit code 0."""
    assert len(SEGMENTATION_LAYOUTS) == 4, "a segmentation layout was dropped"
    assert len(VENDOR_PREFIX_ROSTER) == 11
    assert len(VENDOR_LAYOUT_PROBES) == 44, (
        "the probe set is no longer 11 prefixes x 4 layouts; a shrunken product "
        "reports green over whatever survived"
    )
    assert len({token for _, _, token in VENDOR_LAYOUT_PROBES}) == 44


def test_the_adversary_probe_is_shaped_as_described():
    """Arming. The arm below means nothing if the probe stopped being segmented."""
    body = ADVERSARY_PROBE[len("xoxb-") :]
    assert max(len(part) for part in body.split("-")) == 24, (
        "the probe's longest run is no longer 24, so it no longer demonstrates "
        "that an INTACT secret run was missed"
    )
    assert len(body) - len(body.split("-")[-1]) - 1 == 27


def test_the_adversary_probe_token_is_refused_by_both_detectors():
    """The regression arm. The exact token, fed as INPUT, not a claim about shape."""
    text = "slack " + ADVERSARY_PROBE
    assert scan_text(text) != [], "the tracked-tree sweep missed the segmented xoxb- probe"
    assert pns.scan_for_leaks(text) != [], "THE PUBLISHER missed the segmented xoxb- probe"


@pytest.mark.parametrize(
    ("prefix", "layout", "token"),
    VENDOR_LAYOUT_PROBES,
    ids=[prefix + "/" + layout for prefix, layout, _ in VENDOR_LAYOUT_PROBES],
)
def test_every_vendor_at_every_layout_is_refused_by_both(prefix, layout, token):
    """Vendor x layout, driven as INPUT through both entry points.

    This is the axis a flat-body probe set cannot see. Thirty of these 44 were
    caught by an old detector and missed by both new ones.
    """
    text = "token " + token
    assert scan_text(text) != [], "the sweep missed " + prefix + " at " + layout
    assert pns.scan_for_leaks(text) != [], "THE PUBLISHER missed " + prefix + " at " + layout


#: The three distinct identifiers behind all NINE measured false positives.
#: HAND-WRITTEN here and never imported: an arm that read them out of the
#: detector would be checking the rule against itself. Each ends in a
#: hyphen-segmented English tail whose first three characters spell `sk-`
#: because `task-` does.
INNOCENT_TASK_IDENTIFIERS = (
    "task-argv-does-not-arm",
    "task-argv-is-a-dry-run",
    "task-name-argument-is-dropped",
)


def test_the_innocent_identifiers_are_real_and_still_in_the_tree():
    """Non-vacuity on the SUBJECT. An invented innocent proves nothing."""
    corpus = ""
    for rel in _tracked_text_files():
        if rel in SELF_EXEMPT:
            continue
        try:
            corpus += (REPO_ROOT / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    for ident in INNOCENT_TASK_IDENTIFIERS:
        assert ident in corpus, (
            ident + " is no longer anywhere in the tracked tree, so the "
            "false-positive arms below have lost their subject"
        )


@pytest.mark.parametrize("innocent", INNOCENT_TASK_IDENTIFIERS)
def test_hyphen_segmented_english_is_not_a_credential(innocent):
    """The arm the LEFT BOUNDARY is load-bearing for.

    Remove the boundary from `VendorToken.pattern` and every one of these fires
    again - that is the whole of the nine false positives, and it is why this
    arm is the discriminator's proof rather than decoration.
    """
    assert scan_text("the " + innocent + " case") == [], (
        "the sweep called hyphen-segmented English a credential: " + innocent
    )
    assert pns.scan_for_leaks("the " + innocent + " case") == [], (
        "the publisher called hyphen-segmented English a credential: " + innocent
    )


@pytest.mark.parametrize("innocent", INNOCENT_TASK_IDENTIFIERS)
def test_the_same_tail_at_a_token_boundary_is_a_credential(innocent):
    """The partner guard, and the one that keeps the arm above from being vacuous.

    Same characters, same segmentation, same length - only the left boundary
    differs. `task-` ends in `sk-`, so dropping the leading `ta` turns each
    innocent identifier into a `sk-` token that starts where a token starts. A
    rule that separated these by LENGTH or by CONTIGUITY could not tell this
    pair apart at all.
    """
    boundary_twin = "sk-" + innocent[len("task-") :]
    assert innocent.endswith(boundary_twin[len("sk-") :])
    assert scan_text("token " + boundary_twin) != [], (
        "the sweep missed a credential at a token boundary: " + boundary_twin
    )
    assert pns.scan_for_leaks("token " + boundary_twin) != [], (
        "the publisher missed a credential at a token boundary: " + boundary_twin
    )


# ---------------------------------------------------------------------------
# WHAT THE LEFT BOUNDARY COSTS - the under-fire side, which nothing measured
# ---------------------------------------------------------------------------
#
# THIS IS THE FOURTH RULE IN THIS FILE'S LINEAGE, and the first three were each
# refuted BY MEASUREMENT rather than by argument. Rule 3 - the left boundary
# `(?<![A-Za-z0-9_])` - was adopted because it took the nine false positives to
# zero, and the arms above prove exactly that: `test_hyphen_segmented_english_is
# _not_a_credential` guards the OVER-fire side and
# `test_the_same_tail_at_a_token_boundary_is_a_credential` keeps it honest.
#
# NOTHING GUARDED THE UNDER-FIRE SIDE. A boundary is a subtraction, and the set
# it subtracts was never written down anywhere, so the cost was invisible. An
# independent adversary drove the real publish path into a temp directory and
# found it:
#
#     hand-off line, body 24 repeated capital A, SYNTHETIC:
#       "... cached at ops/runtime/cache_<anthropic prefix><body>.json ..."
#         HEAD's publisher   ->  REFUSE
#         rule 3 scan        ->  []
#         publish()          ->  ok True, TOKEN ON DISK
#
# `git show HEAD:tools/publish_next_session.py` spelled the body with NO left
# boundary at all, so it caught that line, and `TOKEN_<github prefix><body>` and
# `v2<github prefix><body>` with it. Rule 3 missed all three. That is a
# regression against HEAD's own publisher, not only against the sweep.
#
# THE BOUNDARY CLASS, DERIVED rather than adopted. Two populations, both
# measured this run over the 223 tracked files of which 221 are readable after
# `SELF_EXEMPT`:
#
#   POPULATION A, the false positives the boundary exists to kill. The flat wide
#   class at floor 16 with NO boundary produces NINE hits over HEAD's bytes
#   (three in tests/test_responder_task_argv.py, six in
#   tests/test_supervisor_task_argv.py) and TWELVE over the working tree, the
#   extra three being this repair's own prose in tools/publish_next_session.py.
#   The preceding-character census of both is the SAME single-element set:
#   {'a'}. In every one of them `sk-` is the tail of `task-`. A LETTER.
#
#   POPULATION B, the break set. The preceding characters are '_', '_' and '2'.
#   An UNDERSCORE and a DIGIT.
#
# `[A-Za-z]` separates A from B exactly, and it is the only one of the three
# classes tried that does. Measured, floor 16, over the same 221 files:
#
#     no boundary                 ->  12 hits   (9 over HEAD's bytes)
#     (?<![A-Za-z0-9_])  rule 3   ->   0 hits   - and misses all of population B
#     (?<![A-Za-z])      rule 4   ->   0 hits   - and catches all of population B
#
# So rule 4 is rule 3 with `0-9_` removed from the lookbehind. It gives up
# strictly less and keeps the zero.
#
# WHAT IT STILL GIVES UP, and this is the part that now has an arm. A credential
# whose immediately preceding character is a LETTER is missed, at every vendor
# and every layout. `KEY<github prefix><body>` is not refused. That is the price
# of the nine, it is paid deliberately, and the census arm below prints it.

#: SYNTHETIC. A GitHub-shaped prefix over thirty repeated zeros - digits are in
#: every vendor class in the table, and nothing here is or resembles a live key.
#: One token drives the whole census; only the character in FRONT of it varies.
PRECEDING_PROBE_TOKEN = "ghp_" + "0" * 30

#: THE UNIVERSE, derived by subtraction rather than by listing the characters
#: anybody happened to think of. By the time `scan_for_leaks` runs, the block is
#: already known to be 7-bit ASCII: `extract_prompt` raises `non_ascii` BEFORE it
#: calls the leak scan. So the set of things that can immediately precede a token
#: in a hand-off block is exactly the 128 ASCII codepoints, plus the case where
#: there is no preceding character at all.
ASCII_UNIVERSE = frozenset(chr(code) for code in range(128))


def _preceding_character_census() -> tuple[frozenset, frozenset]:
    """`(caught, missed)` over the whole ASCII universe. The cost, measured."""
    caught, missed = set(), set()
    for ch in sorted(ASCII_UNIVERSE):
        (caught if scan_text(ch + PRECEDING_PROBE_TOKEN) else missed).add(ch)
    return frozenset(caught), frozenset(missed)


def test_the_preceding_character_census_covers_the_whole_universe():
    """The floor. A census over an emptied universe is green about nothing."""
    assert len(ASCII_UNIVERSE) == 128
    caught, missed = _preceding_character_census()
    assert caught | missed == ASCII_UNIVERSE
    assert caught & missed == frozenset()
    assert caught, "no preceding character was caught; the probe token is inert"


def test_the_boundary_gives_up_exactly_the_letter_preceded_credentials():
    """THE COST ARM. The boundary's subtraction, stated as a set rather than felt.

    `missed` is what a hand-off may carry past this gate. It is the LETTERS and
    nothing else: an underscore, a digit, a hyphen, a dot, a slash, a quote, a
    space and start-of-string all still refuse. Widen the lookbehind back to
    `(?<![A-Za-z0-9_])` and `_` and the digits move into `missed`, which is the
    regression this arm exists to catch.
    """
    caught, missed = _preceding_character_census()
    assert missed == frozenset(string.ascii_letters), (
        "the boundary's cost is no longer exactly the letter-preceded "
        "credentials; it now gives up " + repr("".join(sorted(missed)))
    )
    assert scan_text(PRECEDING_PROBE_TOKEN) != [], (
        "a credential at the START of the block is missed; start-of-string is "
        "a token boundary and must stay one"
    )


#: A READABLE SAMPLE of both sides of that census, one representative per class
#: a reader would think to ask about. The census above is the exhaustive claim;
#: this is the one a reviewer can check by eye. `expected_caught` is the pin.
PRECEDING_CLASS_PROBES = (
    ("start-of-string", "", True),
    ("space", " ", True),
    ("newline", "\n", True),
    ("underscore", "_", True),
    ("digit", "7", True),
    ("hyphen", "-", True),
    ("dot", ".", True),
    ("forward-slash", "/", True),
    ("back-slash", "\\", True),
    ("double-quote", '"', True),
    ("single-quote", "'", True),
    ("equals", "=", True),
    ("open-angle", "<", True),
    ("letter", "a", False),
    ("upper-letter", "K", False),
)


def test_the_preceding_class_sample_is_not_empty_and_covers_both_verdicts():
    """The floor. A sample that lost its False rows pins only the easy half."""
    assert len(PRECEDING_CLASS_PROBES) == 15
    verdicts = {expected for _, _, expected in PRECEDING_CLASS_PROBES}
    assert verdicts == {True, False}, "the sample no longer shows both sides"


@pytest.mark.parametrize(
    ("name", "preceding", "expected_caught"),
    PRECEDING_CLASS_PROBES,
    ids=[name for name, _, _ in PRECEDING_CLASS_PROBES],
)
def test_each_preceding_character_class_is_pinned_in_both_detectors(
    name, preceding, expected_caught
):
    """Fed as INPUT through both entry points. Not an assertion about a spelling."""
    text = preceding + PRECEDING_PROBE_TOKEN
    swept = scan_text(text) != []
    published = pns.scan_for_leaks(text) != []
    assert swept is expected_caught, (
        "the sweep's verdict changed for a " + name + "-preceded credential"
    )
    assert published is expected_caught, (
        "THE PUBLISHER's verdict changed for a " + name + "-preceded credential"
    )
    assert swept is published, "the sweep and the publisher disagree at " + name


#: THE BREAK SET, verbatim from the adversary that drove the real publish path.
#: Every body is repeated characters and nothing here is or resembles a live
#: key. The first is an underscore-joined PATH, the second an underscore-joined
#: NAME, the third a DIGIT glued to the prefix.
BOUNDARY_BREAK_TOKENS = (
    ("underscore-joined-path", "ops/runtime/cache_" + "sk-ant-api03-" + "A" * 24 + ".json"),
    ("underscore-joined-name", "TOKEN_" + "ghp_" + "B" * 30),
    ("digit-glued-prefix", "v2" + "ghp_" + "B" * 30),
)


def test_the_break_set_is_armed_and_is_not_letter_preceded():
    """Arming. If a break's preceding character became a letter it would prove
    the opposite of what it is here to prove, and would still read as a probe.
    """
    assert len(BOUNDARY_BREAK_TOKENS) == 3
    for name, text in BOUNDARY_BREAK_TOKENS:
        index = max(text.find("sk-ant-"), text.find("ghp_"))
        assert index > 0, name + " has no vendor prefix in it any more"
        assert not text[index - 1].isalpha(), (
            name + " is now letter-preceded, so it no longer probes the break"
        )


@pytest.mark.parametrize(
    ("name", "text"),
    BOUNDARY_BREAK_TOKENS,
    ids=[name for name, _ in BOUNDARY_BREAK_TOKENS],
)
def test_the_break_set_is_caught_by_both_detectors(name, text):
    """The regression arm for rule 3. HEAD's boundary-free publisher caught all
    three of these; rule 3 caught none. Driven as INPUT, through both.
    """
    assert scan_text(text) != [], "the tracked-tree sweep missed " + name
    assert pns.scan_for_leaks(text) != [], "THE PUBLISHER missed " + name


# ---------------------------------------------------------------------------
# THE NAME-VALUE SEPARATOR - what may sit between a rostered name and its value
# ---------------------------------------------------------------------------
#
# THE DEFECT IS PRE-EXISTING AT HEAD 69e4e9d, not introduced by the repairs
# landed alongside it. Both detectors spelled the gap between the name and the
# value as one optional double quote, then a SINGLE colon or equals, with only
# whitespace either side. Measured 2026-09-11 by driving the real `publish()`
# into a temp directory with a DUMMY body of forty repeated `D` - synthetic,
# carrying no vendor prefix and resembling no live credential:
#
#     CONTROL bare NAME=value        1 hit   REFUSED
#     CONTROL NAME = value           1 hit   REFUSED
#     markdown inline code name      0 hits  PUBLISHED, dummy on disk
#     markdown bold name             0 hits  PUBLISHED, dummy on disk
#     markdown table row             0 hits  PUBLISHED, dummy on disk
#     python dict single-quoted key  0 hits  PUBLISHED, dummy on disk
#     yaml single-quoted key         0 hits  PUBLISHED, dummy on disk
#     makefile conditional assign    0 hits  PUBLISHED, dummy on disk
#     shell append assign            0 hits  PUBLISHED, dummy on disk
#     arrow note                     0 hits  PUBLISHED, dummy on disk
#
# THE NAME PATH IS THE SOLE DETECTOR FOR ONE ROSTERED NAME. No row of
# `VENDOR_TOKENS` covers a Nimble credential, so `NIMBLE_API_KEY` has no prefix
# path behind it - `GEMINI_API_KEY` has `AIza`, `RIOT_API_KEY` has `RGAPI-`,
# Anthropic has `sk-ant-`. Nimble's real format is NOT derivable from this tree
# and is not asserted here.
#
# THE POPULATION, DERIVED BY SUBTRACTION over the ASCII universe rather than by
# listing the shapes somebody happened to probe. By the time either detector
# runs the text is known 7-bit ASCII, so the universe is the 128 codepoints.
# Subtracted, each with its reason:
#
#   1. Letters and digits - a word character adjacent to the name means either
#      the name is a prefix of a longer identifier, or an INTERVENING WORD has
#      begun. An intervening word is the no-operator prose case, which is out
#      of scope below. THIS IS THE LINE AGAINST A PROXIMITY HEURISTIC: the
#      separator can never cross a word, so its reach is bounded by syntax
#      rather than by a character count somebody picked.
#   2. Newline and carriage return, FROM THE WIDENED ALTERNATIVE ONLY. Its gap
#      is a space-or-tab class, so it is line-bounded and cannot walk out of a
#      markdown table cell across a line break into the separator row below and
#      call the leading pipe a value - a false positive measured while deriving
#      this. The REPLACED shape is kept verbatim as a second alternative, so a
#      binding whose value sits on the next line is still caught exactly as it
#      was. The widening is a strict SUPERSET and loses no detection.
#   3. Comma and semicolon - they close the current item, so what follows
#      belongs to the next one rather than to this name.
#   4. Dot, forward slash and backslash - they make the name part of a dotted
#      expression or a path, which is not a binding.
#   5. Hash - begins a comment, so what follows is commentary, not a value.
#   6. Percent, dollar, ampersand, at, bang, caret - value-side sigils. The
#      percent and dollar forms are the EXEMPTION's business and have to reach
#      it WHOLE.
#   7. Left angle - it opens an angle placeholder on the value side. Swallowing
#      it would hand the exemption a truncated value and turn every placeholder
#      into a false positive. Measured while deriving this, which is why right
#      angle is in the class and left angle is not.
#   8. Opening quotes and brackets on the RIGHT of the operator - left to
#      `VALUE_CAPTURE`, which owns the value's own quoting. A separator that ate
#      the opening quote would hand the exemption a value it could not parse.
#
# What survives sits in three roles, and the census arms below RE-DERIVE the
# whole thing from the live pattern rather than trusting this comment.
#
# OUT OF SCOPE, RECORDED WITH ITS MEASUREMENT rather than fixed here:
#
#   A. NO OPERATOR AT ALL - the prose shapes that write the name, then an
#      English word, then the value. Measured 0 hits at HEAD and 0 hits after
#      this widening, and that is deliberate. Catching it needs a
#      proximity-or-entropy rule: a detector that fires on a name and a
#      high-entropy run within N characters REGARDLESS of what lies between.
#      That is a different detector CLASS with its own false-positive budget -
#      every prose sentence naming a rostered key becomes a candidate - and it
#      is not derivable from the separator. An adversary ranks it the MOST
#      plausible shape in an agent-written hand-off, so it is the next thing to
#      scope, not the least.
#   B. OFF-ROSTER NAMES bound to a value carrying no vendor prefix. Invisible
#      to BOTH paths by construction: the name path iterates `SECRET_NAMES` and
#      the prefix path iterates `VENDOR_TOKENS`, and such a line is in neither.
#      Measured 0 hits before and after. That is a ROSTER-COMPLETENESS
#      question, not a matcher question, and the roster is not extended on one
#      slice's judgement.

#: SYNTHETIC. Forty repeated `D`: no vendor prefix, no entropy, and resembling
#: no live credential. The NAME is the evidence in this detector, not the value,
#: which is exactly what makes a dummy body sufficient to probe it.
SEPARATOR_DUMMY = "D" * 40

#: IN SCOPE. Every row must be REFUSED by both detectors. The first two are the
#: CONTROLS - they were already refused at HEAD, so if they ever go quiet the
#: failure is in the name path itself and not in the widening.
SEPARATOR_PROBES = (
    ("control-bare-equals", "NIMBLE_API_KEY=" + SEPARATOR_DUMMY),
    ("control-spaced-equals", "NIMBLE_API_KEY = " + SEPARATOR_DUMMY),
    ("json-double-quoted-key", '"NIMBLE_API_KEY": "' + SEPARATOR_DUMMY + '"'),
    ("markdown-inline-code", "`NIMBLE_API_KEY`: " + SEPARATOR_DUMMY),
    ("markdown-bold-stars", "**NIMBLE_API_KEY**: " + SEPARATOR_DUMMY),
    ("markdown-bold-underscores", "__NIMBLE_API_KEY__: " + SEPARATOR_DUMMY),
    ("markdown-table-row", "| NIMBLE_API_KEY | " + SEPARATOR_DUMMY + " |"),
    ("python-dict-single-quoted", "{'NIMBLE_API_KEY': '" + SEPARATOR_DUMMY + "'}"),
    ("yaml-single-quoted-key", "'NIMBLE_API_KEY': " + SEPARATOR_DUMMY),
    ("makefile-conditional", "NIMBLE_API_KEY ?= " + SEPARATOR_DUMMY),
    ("makefile-immediate", "NIMBLE_API_KEY := " + SEPARATOR_DUMMY),
    ("shell-append", "NIMBLE_API_KEY+=" + SEPARATOR_DUMMY),
    ("arrow-note", "NIMBLE_API_KEY -> " + SEPARATOR_DUMMY),
    ("fat-arrow-note", "NIMBLE_API_KEY => " + SEPARATOR_DUMMY),
    ("spaced-colon", "NIMBLE_API_KEY : " + SEPARATOR_DUMMY),
    ("tab-separated", "NIMBLE_API_KEY\t=\t" + SEPARATOR_DUMMY),
)

#: OUT OF SCOPE, pinned at the reading MEASURED rather than at the reading
#: wanted. Every row must still PUBLISH. Flipping one of these to refused is a
#: decision about a DIFFERENT detector class, and it should turn this red so
#: that the decision gets made rather than drifted into.
OUT_OF_SCOPE_BINDINGS = (
    ("no-operator-prose-is", "NIMBLE_API_KEY is " + SEPARATOR_DUMMY),
    ("no-operator-prose-set-to", "set NIMBLE_API_KEY to " + SEPARATOR_DUMMY),
    ("off-roster-github-token", "GITHUB_TOKEN=" + SEPARATOR_DUMMY),
    ("off-roster-password", "PASSWORD=" + SEPARATOR_DUMMY),
    ("off-roster-aws", "AWS_SECRET_ACCESS_KEY=" + SEPARATOR_DUMMY),
)

#: THE EXEMPTIONS THE WIDENING MUST NOT BREAK. Every row is a LOOKUP, and the
#: first four were each fixed by an earlier repair; a widening that refuses one
#: of these has eaten its own destination.
SEPARATOR_EXEMPT = (
    ("powershell-env-binding", "$env:GEMINI_API_KEY = $key"),
    ("percent-reference", "NIMBLE_API_KEY=%NIMBLE_API_KEY%"),
    ("braced-lowercase-reference", "NIMBLE_API_KEY=${nimble_key}"),
    (
        "dotnet-getenvironmentvariable",
        'NIMBLE_API_KEY = [Environment]::GetEnvironmentVariable("NIMBLE_API_KEY")',
    ),
    ("angle-placeholder", "NIMBLE_API_KEY: <REDACTED>"),
    ("angle-placeholder-bold", "**NIMBLE_API_KEY**: <REDACTED>"),
    ("os-environ-lookup", "NIMBLE_API_KEY = os.environ['NIMBLE_API_KEY']"),
)


def test_the_separator_probe_sets_are_not_empty():
    """THE FLOOR. An emptied parametrize is `1 skipped` at exit 0, which reads
    as a pass. The counts are asserted so emptying a set is a RED rather than a
    quiet nothing.
    """
    assert len(SEPARATOR_PROBES) == 16
    assert len(OUT_OF_SCOPE_BINDINGS) == 5
    assert len(SEPARATOR_EXEMPT) == 7
    assert len(SEPARATOR_DUMMY) == 40
    assert set(SEPARATOR_DUMMY) == {"D"}, "the dummy body stopped being a dummy"


@pytest.mark.parametrize(
    ("name", "text"),
    SEPARATOR_PROBES,
    ids=[name for name, _ in SEPARATOR_PROBES],
)
def test_every_in_scope_separator_is_caught_by_both_detectors(name, text):
    """Driven as INPUT through both detectors. Not an assertion about a spelling.

    THE TWO MUST AGREE. `SECRET_BINDING` here and the name loop in
    `scan_for_leaks` share ONE separator constant, so a disagreement means the
    single source stopped being single.
    """
    assert pns.scan_for_leaks(text) != [], "THE PUBLISHER missed " + name
    assert scan_text(text) != [], "the tracked-tree sweep missed " + name


@pytest.mark.parametrize(
    ("name", "text"),
    OUT_OF_SCOPE_BINDINGS,
    ids=[name for name, _ in OUT_OF_SCOPE_BINDINGS],
)
def test_the_out_of_scope_shapes_are_pinned_at_their_measured_reading(name, text):
    """THE COST ARM. These are MISSED, deliberately, and the miss is recorded
    here so the next reader inherits a measurement instead of rediscovering a
    hole. See sections A and B in the note above for why each needs a different
    mechanism than a wider separator.
    """
    assert pns.scan_for_leaks(text) == [], name + " changed reading without a ruling"
    assert scan_text(text) == [], name + " changed reading without a ruling"


@pytest.mark.parametrize(
    ("name", "text"),
    SEPARATOR_EXEMPT,
    ids=[name for name, _ in SEPARATOR_EXEMPT],
)
def test_the_widening_does_not_eat_its_own_destination(name, text):
    """NON-VACUITY. A separator class that refused everything would pass every
    in-scope arm above and be useless. These rows prove it still has a subject.
    """
    assert pns.scan_for_leaks(text) == [], "THE PUBLISHER refused a lookup: " + name
    assert scan_text(text) == [], "the sweep refused a lookup: " + name


def _separator_character_census() -> tuple[frozenset, frozenset]:
    """`(caught, missed)` for a SINGLE character standing between a rostered
    name and a dummy value, over the whole ASCII universe. The population is
    re-derived from the LIVE pattern here, so the subtraction note above is
    checkable rather than merely readable.
    """
    caught, missed = set(), set()
    for ch in sorted(ASCII_UNIVERSE):
        text = "NIMBLE_API_KEY" + ch + SEPARATOR_DUMMY
        (caught if pns.scan_for_leaks(text) else missed).add(ch)
    return frozenset(caught), frozenset(missed)


def test_the_separator_census_covers_the_whole_universe():
    """The floor under the census. A census over an emptied universe is green
    about nothing.
    """
    assert len(ASCII_UNIVERSE) == 128
    caught, missed = _separator_character_census()
    assert caught | missed == ASCII_UNIVERSE
    assert caught & missed == frozenset()


def test_the_single_character_separator_class_is_exactly_the_derived_one():
    """THE SUBTRACTION, ASSERTED. A single character standing between name and
    value is a separator only if it is one of the four BINDING glyphs - colon,
    equals, pipe, right-angle. Decoration and gap characters alone are NOT a
    binding: they need a binding glyph beside them, which is what keeps this a
    SYNTAX rule rather than a proximity rule.
    """
    caught, _ = _separator_character_census()
    assert caught == frozenset(":=|>"), (
        "the single-character separator class drifted to " + repr(sorted(caught))
    )


def test_no_word_character_is_ever_a_separator():
    """THE LINE AGAINST A PROXIMITY HEURISTIC, asserted rather than described.

    If a letter, digit or underscore could stand between the name and the
    value, the detector would be reading across an intervening WORD, which is
    the out-of-scope prose case wearing the separator's clothes.
    """
    caught, _ = _separator_character_census()
    word_chars = {ch for ch in ASCII_UNIVERSE if ch.isalnum() or ch == "_"}
    assert caught & word_chars == frozenset(), (
        "a word character became a separator: " + repr(sorted(caught & word_chars))
    )


def test_the_widening_loses_no_detection_the_replaced_shape_made():
    """STRICT SUPERSET, asserted at the two places it could have been violated.

    A widening that quietly drops a case is a regression wearing a repair's
    clothes, and this tree has shipped one before: a left-boundary rule adopted
    for its false-positive score turned out to miss three tokens the shape it
    replaced had caught. So the replaced spelling is kept VERBATIM as a second
    alternative and both halves are pinned - the value on the NEXT LINE, which
    only the legacy alternative reaches, and the widened line-bounded form.
    """
    across_lines = "NIMBLE_API_KEY =\n" + SEPARATOR_DUMMY
    assert pns.scan_for_leaks(across_lines) != [], "THE PUBLISHER lost a detection"
    assert scan_text(across_lines) != [], "the sweep lost a detection"
    assert r"\"?\s*[:=]\s*" in pns.NAME_VALUE_SEPARATOR, (
        "the replaced shape is gone from the separator, so the superset claim "
        "above is no longer true and the next-line case rests on nothing"
    )


def test_the_widened_alternative_is_line_bounded():
    """The measured false positive the space-or-tab gap exists to prevent: a
    markdown table cell whose name ends the row, with the separator row under
    it. A whitespace gap walks across the break and calls the leading pipe a
    value. Driven through both detectors.
    """
    table = "| NIMBLE_API_KEY |\n| --- |\n"
    assert pns.scan_for_leaks(table) == [], "the separator walked across a line"
    assert scan_text(table) == [], "the separator walked across a line"


def test_the_separator_is_one_object_shared_by_both_detectors():
    """The anti-drift arm. Two hand-maintained copies of this spelling is what
    the defect above was MADE of: the sweep restated the publisher's separator
    and therefore inherited every one of its misses, so there was no second
    line of defence over the committed tree either.
    """
    assert pns.NAME_VALUE_SEPARATOR in SECRET_BINDING.pattern, (
        "the sweep no longer builds its binding from the publisher's separator"
    )
