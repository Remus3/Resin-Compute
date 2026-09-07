"""Where `wish_authkey` looks for webCaches, and how long a URL it will keep.

WHY THIS MODULE EXISTS. Both properties failed silently in the field on
2026-09-07, during the only first run this account will ever have, and neither
failure looked like a failure.

THE FIRST DEFECT: A WRONG DIRECTORY AND A MISSING ONE PRINTED THE SAME SENTENCE.
`tools/wish_authkey.py` was written against
`%USERPROFILE%/AppData/LocalLow/miHoYo/Genshin Impact/GenshinImpact_Data/webCaches`,
which is where most public write-ups put it. Under the current HoYoPlay layout
it is not there at all - it is under the GAME INSTALL. So `--scan` reported
"no webCaches directory found yet. Has Genshin Impact ever been launched on
this machine?" while the operator had the in-game Wish History page open in
front of them and the cache held 15 ASCII occurrences of "authkey". The message
was not wrong about what it checked; it was wrong about what it implied, which
is worse, because it sent the reader to look at the game rather than at the
path.

The fix makes resolution a list of candidates tried in order. This module pins
the ORDER, not just the membership: an install-root candidate must precede the
user-profile one, because the user-profile path is the one that was wrong and
putting it first would restore the defect while keeping the new code shape.

THE SECOND DEFECT, AND WHY IT IS TESTED HERE THOUGH IT NEVER SHIPPED. A scratch
extractor written the same hour capped URL candidates at 1500 bytes. The real
captured URL is 1755 bytes, of which the authkey alone is 1452, so the cap cut
the credential in half and the API answered `retcode -100: authkey error`. That
reads exactly like an expired or malformed key - a server-side problem - and
the first instinct was to go and get a fresh one rather than to look at the
scanner. `tools/wish_authkey.py` itself was never vulnerable: its cap is 4096.
The point of pinning it is that 4096 is not an arbitrary round number any more.
It is a number with a measurement behind it, and anyone lowering it toward
"about a kilobyte, surely enough for a URL" is reintroducing a defect whose
symptom points somewhere else entirely.

The measured figures, all from the capture of 2026-09-07:

    full captured URL      1755 bytes
    authkey value alone    1452 bytes
    _MAX_CANDIDATE_BYTES   4096

No real authkey appears in this file. The synthetic one below is obviously
invented, per the standing rule that a fixture planting a real credential IS
the leak it claims to test for.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "wish_authkey.py"


def _load_module():
    """Import `tools/wish_authkey.py` by path.

    `tools/` has no `__init__.py` and is not a package, which is the same
    reason `mypy.ini` records `scripts/` as blocked on a duplicate-module-name
    refusal. Loading by spec keeps this test independent of that.
    """
    spec = importlib.util.spec_from_file_location("_wish_authkey_under_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def wish_authkey():
    return _load_module()


# ---------------------------------------------------------------------------
# The measurements this module exists to defend
# ---------------------------------------------------------------------------

#: Length in bytes of the real gacha URL captured on 2026-09-07. The value is
#: recorded, the URL is not - it carried a live credential.
MEASURED_CAPTURED_URL_BYTES = 1755

#: Length of the authkey VALUE inside that URL, measured the same way.
MEASURED_AUTHKEY_VALUE_BYTES = 1452


def test_the_candidate_list_puts_an_install_root_before_the_user_profile():
    """Order is the property. Membership alone would pass with the bug intact."""
    module = _load_module()
    candidates = [str(path).replace("\\", "/") for path in module._web_caches_candidates()]
    assert candidates, "no candidates at all, so the comparison would be vacuous"

    install_positions = [
        index for index, path in enumerate(candidates)
        if "GenshinImpact_Data/webCaches" in path and "AppData/LocalLow" not in path
    ]
    profile_positions = [
        index for index, path in enumerate(candidates)
        if "AppData/LocalLow" in path
    ]
    assert install_positions, (
        "no game-install candidate is present. The measured location of "
        "webCaches on this machine is under the install, not the user profile."
    )
    assert profile_positions, (
        "the user-profile candidate was deleted rather than demoted. It is "
        "kept deliberately: an older install may still use it."
    )
    assert min(install_positions) < min(profile_positions), (
        "the user-profile path is being tried before any install path, which "
        "is the exact ordering that produced a false 'no webCaches directory "
        "found yet' on 2026-09-07. Candidates were: " + repr(candidates)
    )


def test_the_environment_override_wins_and_actually_resolves(tmp_path, monkeypatch):
    """Positive control for the resolver: point it somewhere real, it goes there.

    Without this arm, `_web_caches_root` returning a plausible-looking path and
    returning the RIGHT path are indistinguishable - the same shape of mistake
    that let the original defect through.
    """
    module = _load_module()
    planted = tmp_path / "webCaches"
    (planted / "9.99.0.0").mkdir(parents=True)

    monkeypatch.setenv(module._WEBCACHES_ENV, str(planted))
    resolved = module._web_caches_root()
    assert resolved == planted, (
        "the override did not win. Resolved to " + repr(str(resolved))
    )

    versions = module.find_web_caches()
    assert [p.name for p in versions] == ["9.99.0.0"], (
        "the resolver found the root but the version walk did not follow it: "
        + repr([str(p) for p in versions])
    )


def test_an_absent_override_does_not_hijack_resolution(tmp_path, monkeypatch):
    """An override naming a path that does not exist must fall through, not win.

    A resolver that trusted the override blindly would answer with a directory
    nobody can read, and `find_web_caches` would return the empty list - which
    is the SAME answer as "the game has never run". That collapse of two
    different facts into one answer is the defect this module is named after.
    """
    module = _load_module()
    monkeypatch.setenv(module._WEBCACHES_ENV, str(tmp_path / "nope" / "webCaches"))
    candidates = module._web_caches_candidates()
    assert len(candidates) > 1, (
        "with an override set there must still be fallbacks behind it"
    )
    resolved = module._web_caches_root()
    assert resolved != candidates[0] or resolved.is_dir(), (
        "a non-existent override was returned as the resolved root"
    )


def test_the_candidate_byte_cap_clears_a_real_captured_url():
    """4096 is a measured number, not a round one. Keep the margin honest."""
    module = _load_module()
    cap = module._MAX_CANDIDATE_BYTES
    assert cap >= MEASURED_CAPTURED_URL_BYTES, (
        "_MAX_CANDIDATE_BYTES is "
        + str(cap)
        + " but a real captured gacha URL measured "
        + str(MEASURED_CAPTURED_URL_BYTES)
        + " bytes on 2026-09-07. A cap below that truncates the authkey and "
        "the endpoint answers 'retcode -100: authkey error', which reads as an "
        "expired key rather than as a scanner bug."
    )
    assert cap >= MEASURED_AUTHKEY_VALUE_BYTES * 2, (
        "the margin over the authkey value alone ("
        + str(MEASURED_AUTHKEY_VALUE_BYTES)
        + " bytes) is too thin to survive a longer key or a longer query string"
    )


def test_a_long_synthetic_url_survives_extraction_intact():
    """End to end over the scanner, with a URL as long as the real one.

    The cap assertion above checks a constant. This checks the code path that
    reads it, because a constant can be correct while the loop using it is off
    by a factor - the UTF-16LE scanner multiplies the cap by two and that is
    exactly the sort of place a units error hides.
    """
    module = _load_module()
    fake_key = "AAAA1111BBBB2222" * 100  # 1600 chars, obviously invented
    url = (
        "https://public-operation-hk4e-sg.hoyoverse.com/gacha_info/api/getGachaLog"
        "?authkey_ver=1&sign_type=2&auth_appid=webview_gacha&lang=en"
        "&region=os_usa&authkey=" + fake_key + "&game_biz=hk4e_global"
    )
    assert len(url) >= MEASURED_CAPTURED_URL_BYTES, (
        "the synthetic URL is shorter than the real one, so this arm would not "
        "have caught the real truncation"
    )

    noise = bytes(range(256)) * 8
    blob = noise + url.encode("ascii") + noise + url.encode("utf-16-le") + noise

    found = module.extract_urls(blob)
    gacha = module.select_gacha_urls(found)
    assert gacha, "nothing extracted at all, so the length check below is vacuous"
    assert url in gacha, (
        "the URL came back but not intact. Longest candidate was "
        + str(max(len(candidate) for candidate in gacha))
        + " bytes against an input of "
        + str(len(url))
    )

    redacted = module._redact_url(url)
    assert fake_key not in redacted, "redaction failed open on a long key"
    assert "authkey=" in redacted, "redaction removed the parameter name too"
