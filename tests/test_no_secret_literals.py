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
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

from tests.conftest import require_git_repository

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Vendor prefixes that identify a real credential. A sha256 digest, a git SHA
#: and a base64 blob never carry one, which is what makes these safe to sweep.
VENDOR_TOKEN = re.compile(
    r"(?:sk-ant-[A-Za-z0-9_\-]{16,}"
    r"|sk-[A-Za-z0-9]{20,}"
    r"|ghp_[A-Za-z0-9]{30,}"
    r"|github_pat_[A-Za-z0-9_]{30,}"
    r"|AIza[A-Za-z0-9_\-]{30,}"
    r"|RGAPI-[0-9a-f\-]{30,}"
    r"|xox[bapsr]-[A-Za-z0-9\-]{20,})"
)

#: The secret-bearing variable names in use on this machine, 2026-09-06. Held
#: as a literal set rather than read from the environment: a guard that asked
#: the live environment would go SILENT on a machine where the variables are
#: not set, which is every CI runner and every fresh clone.
SECRET_NAMES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_USAGE_KEY",
    "NIMBLE_API_KEY",
    "GEMINI_API_KEY",
    "RIOT_API_KEY",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
)

#: `NAME = "value"` / `"NAME": "value"` / `NAME=value`, where value is a bare
#: literal of any length. Length is deliberately NOT part of the test: a short
#: value bound to one of these names is either a secret or a placeholder, and a
#: placeholder should be an env reference too.
SECRET_BINDING = re.compile(
    r"(?:" + "|".join(SECRET_NAMES) + r")"
    r"\"?\s*[:=]\s*"
    r"(?P<value>\"[^\"]*\"|'[^']*'|[^\s,}]+)"
)

#: Referencing the environment is the CORRECT pattern and stays legal. Anything
#: matching one of these as the bound value is a lookup, not a literal.
ENV_REFERENCE = re.compile(
    r"(?:os\.environ|getenv|GetEnvironmentVariable|\$env:|\$\{?[A-Z_]+\}?|%[A-Z_]+%"
    r"|secrets\.|vars\.|MOVED-TO-|<[^>]*>|xxx|XXX|placeholder|PLACEHOLDER)",
)

#: A bound value that IS a variable reference in its ENTIRETY - PowerShell or
#: shell `$key` - is a lookup rather than a literal.
#:
#: Anchored deliberately, and kept OUT of `ENV_REFERENCE`. That pattern is
#: applied with `.search()`, so folding a bare `$name` into it would exempt any
#: value merely CONTAINING one, and `"abc$key"` - a real literal with a variable
#: spliced in - would go quiet. The arms below hold both halves.
#:
#: Reported by Legion Wallpaper on 2026-09-07 against its own ported copy:
#: `$env:GEMINI_API_KEY = $key` was flagged although `$key` had been read from
#: `GetEnvironmentVariable` on the line above. That is the CORRECT destination
#: and the guard called it a leak. Latent here rather than live - this tree
#: tracks one `.ps1` and no instance of the shape - and a false positive is
#: worth closing before it teaches a reader to wave the guard through.
VARIABLE_VALUE = re.compile(r"^\$[A-Za-z_][A-Za-z0-9_]*$")

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
        if ENV_REFERENCE.search(value):
            continue
        if VARIABLE_VALUE.match(value.strip("\"'")):
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


#: The PowerShell shape Legion Wallpaper measured: a variable holding a value
#: already read from the environment, assigned to the env destination. Built
#: from `chr(36)` so this module's own text does not carry the literal binding
#: it is describing.
_DOLLAR = chr(36)
_WHOLE_VARIABLE = f"{_DOLLAR}env:GEMINI_API_KEY = {_DOLLAR}key"
_SPLICED_VARIABLE = f'GEMINI_API_KEY = "abc{_DOLLAR}key"'
_TRAILING_LITERAL = f'GEMINI_API_KEY={_DOLLAR}key"abc123"'


def test_a_value_that_is_wholly_a_variable_reference_is_a_lookup():
    """The false positive LW reported, closed - and the check is ARMED first.

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
