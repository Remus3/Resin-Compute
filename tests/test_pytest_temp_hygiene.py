"""Pin the temp-hygiene decision this tree actually measured, not the one that
sounds right.

The shared pile lives at %TEMP%/pytest-of-<user>. That root is keyed to the
USER, not to the repo, so every repository on this host writes into one place
and this repo's pytest.ini governs only this repo's runs. Measured 2026-09-20:
one full `python -m pytest tests` here left 163 files across two numbered
directories, which is not the source of a six-figure pile.

The 2026-09-20 measurement found `tmp_path_retention_count` was not what kept
numbered roots alive on this host: of 14 numbered roots, 12 were already
cleanup candidates under pytest's default keep=3 and every one was refused by
`_pytest.pathlib.ensure_deletable` on a `.lock` younger than `LOCK_TIMEOUT`
(259200 s, 72 hours, a module constant no ini key reaches). That finding still
stands as a fact about lock age.

MAIN FIX TEMP-1 (2026-10-09, SHA-256 verified, operator authority) supersedes
the earlier conclusion that the key should stay undeclared. It orders
`tmp_path_retention_policy = failed` AND `tmp_path_retention_count = 1`, after
measuring 16 basetemp dirs and 22,876 entries in one of this tree's session
scratchpads. Decision recorded: adopt 1. Alternative rejected: keep pytest's
default 3. Reversed by: a MAIN ruling.

These arms pin both settings, declared and effective, so a later reader cannot
quietly drop either one.

This module carries NO allowlist, exemption or known-good set. Every value it
asserts was read off a run of this tree on this host, and none was admitted
because the reasoning sounded right.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTEST_INI = REPO_ROOT / "pytest.ini"

# pytest's own default for tmp_path_retention_count, read off
# _pytest/tmpdir.py::pytest_addoption on 2026-09-20 under pytest 9.0.3.
PYTEST_OWN_RETENTION_COUNT_DEFAULT = "3"

# The value MAIN FIX TEMP-1 (2026-10-09, SHA-256 verified) orders this tree to
# declare. Reversed only by a MAIN ruling.
ORDERED_RETENTION_COUNT = "1"


def _declared() -> configparser.ConfigParser:
    """pytest.ini as a PARSED mapping, so a commented-out key reads as absent."""
    parser = configparser.ConfigParser()
    parser.read(PYTEST_INI, encoding="utf-8")
    return parser


def test_tmp_path_retention_policy_is_declared_and_effective_is_failed(
    pytestconfig: pytest.Config,
) -> None:
    parser = _declared()
    assert parser.has_option("pytest", "tmp_path_retention_policy"), (
        "pytest.ini must DECLARE tmp_path_retention_policy. It decides whether a "
        "PASSED test's own tmp_path directory survives the session; pytest's own "
        "default is 'all', which keeps every one of them. Declaring it is the "
        "single setting in this file that moves measured temp behaviour."
    )
    assert parser.get("pytest", "tmp_path_retention_policy").strip() == "failed", (
        "tmp_path_retention_policy must be 'failed'. 'all' keeps every passed "
        "test's tmp_path directory, and 'none' deletes a FAILED test's directory "
        "too - that directory is the evidence somebody will want when the failure "
        "is investigated. Do not trade it away for temp space."
    )
    assert pytestconfig.getini("tmp_path_retention_policy") == "failed", (
        "the EFFECTIVE tmp_path_retention_policy is not 'failed'. pytest.ini "
        "declares it, so something on the command line or in a nearer config is "
        "overriding the setting that bounds this tree's own temp footprint."
    )


def test_tmp_path_retention_count_effective_value_is_one(
    pytestconfig: pytest.Config,
) -> None:
    effective = pytestconfig.getini("tmp_path_retention_count")
    assert str(effective) == ORDERED_RETENTION_COUNT, (
        "the EFFECTIVE tmp_path_retention_count is "
        f"{effective!r}, not {ORDERED_RETENTION_COUNT!r}. MAIN FIX TEMP-1 "
        "(2026-10-09) orders tmp_path_retention_count = 1 alongside "
        "tmp_path_retention_policy = failed: one session scratchpad here was "
        "measured holding 16 basetemp dirs and 22,876 entries. pytest's own "
        f"default is {PYTEST_OWN_RETENTION_COUNT_DEFAULT!r}, so an effective "
        "value of 3 means the pytest.ini line is missing or overridden. "
        "Reversed only by a MAIN ruling."
    )


def test_pytest_ini_declares_retention_count_one_per_main_fix_temp_1() -> None:
    parser = _declared()
    assert parser.has_option("pytest", "tmp_path_retention_count"), (
        "pytest.ini must DECLARE tmp_path_retention_count. MAIN FIX TEMP-1 "
        "(2026-10-09) orders it set to 1; pytest's own default is "
        f"{PYTEST_OWN_RETENTION_COUNT_DEFAULT!r}, which is what an absent key "
        "silently yields."
    )
    declared = parser.get("pytest", "tmp_path_retention_count").strip()
    assert declared == ORDERED_RETENTION_COUNT, (
        f"pytest.ini declares tmp_path_retention_count = {declared!r}; MAIN FIX "
        f"TEMP-1 orders {ORDERED_RETENTION_COUNT!r}. Reversed only by a MAIN "
        "ruling."
    )
