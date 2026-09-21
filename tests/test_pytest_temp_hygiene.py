"""Pin the temp-hygiene decision this tree actually measured, not the one that
sounds right.

The shared pile lives at %TEMP%/pytest-of-<user>. That root is keyed to the
USER, not to the repo, so every repository on this host writes into one place
and this repo's pytest.ini governs only this repo's runs. Measured 2026-09-20:
one full `python -m pytest tests` here left 163 files across two numbered
directories, which is not the source of a six-figure pile.

Two controls decided what this file pins.

* `tmp_path_retention_count` defaults to the string "3" inside pytest itself
  (`_pytest/tmpdir.py`, `pytest_addoption`). Writing `tmp_path_retention_count
  = 3` into pytest.ini therefore restates a default and changes nothing.
* Root pruning on this host is not failing on that count. Of 14 numbered
  roots present, 12 were already cleanup candidates under keep=3, and every
  one was refused by `_pytest.pathlib.ensure_deletable` because it still
  carried a `.lock` younger than `LOCK_TIMEOUT` - 259200 s, that is 72 hours,
  a module constant no ini key reaches. A control in a private root
  reproduced the split exactly: given ten numbered directories where the even
  ones carried a fresh lock, keep=3 spared the newest three and then removed
  only the unlocked candidates, leaving every locked candidate standing.

So the supported change was no new setting at all. These arms pin that
decision so a later reader cannot quietly add the no-op line, or quietly
delete the one setting that does move measured behaviour.

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


def test_tmp_path_retention_count_is_left_at_pytests_own_default(
    pytestconfig: pytest.Config,
) -> None:
    effective = pytestconfig.getini("tmp_path_retention_count")
    assert effective == PYTEST_OWN_RETENTION_COUNT_DEFAULT, (
        "the EFFECTIVE tmp_path_retention_count is "
        f"{effective!r}, not {PYTEST_OWN_RETENTION_COUNT_DEFAULT!r}. That key "
        "governs how many numbered pytest-N ROOT directories survive under "
        "%TEMP%/pytest-of-<user>. Changing it was measured NOT to shrink that "
        "pile on this host: 12 of 14 roots were already cleanup candidates under "
        "keep=3 and every one was refused on lock age by "
        "_pytest.pathlib.ensure_deletable, whose LOCK_TIMEOUT of 72 hours no ini "
        "key can reach. If you are changing it anyway, bring a before/after count "
        "of the surviving root directories and update this arm with it."
    )


def test_pytest_ini_does_not_restate_the_retention_count_default() -> None:
    parser = _declared()
    assert not parser.has_option("pytest", "tmp_path_retention_count"), (
        "pytest.ini declares tmp_path_retention_count, which pytest already "
        "defaults to "
        f"{PYTEST_OWN_RETENTION_COUNT_DEFAULT!r}. A config line that restates its "
        "own default moves no behaviour and is worse than no line at all, because "
        "the next reader will believe the pile is bounded by it. It is not: the "
        "block is a stale .lock newer than LOCK_TIMEOUT, not the keep count. See "
        "the measured comment block in pytest.ini before re-adding this."
    )
