"""Regression test: pytest.ini must cap tmp_path retention.

A sibling measured 68,630 leftover temp files from about 9 pytest runs on this
shared host, stalling logon by roughly 155 s. `tmp_path_retention_policy =
failed` keeps only the tmp_path dirs of failed tests. This test parses
pytest.ini with configparser and asserts the key is present and correct,
without disturbing any other existing key.
"""
from __future__ import annotations

import configparser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTEST_INI = REPO_ROOT / "pytest.ini"


def _parse() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(PYTEST_INI, encoding="utf-8")
    return parser


def test_tmp_path_retention_policy_is_failed() -> None:
    parser = _parse()
    assert parser.has_section("pytest"), "pytest.ini must carry a [pytest] section"
    assert parser.has_option("pytest", "tmp_path_retention_policy")
    value = parser.get("pytest", "tmp_path_retention_policy").strip()
    assert value == "failed"


def test_existing_addopts_unchanged() -> None:
    parser = _parse()
    addopts = parser.get("pytest", "addopts").strip()
    assert addopts == "-q --strict-markers --strict-config"


def test_existing_norecursedirs_unchanged() -> None:
    parser = _parse()
    norecursedirs = parser.get("pytest", "norecursedirs").strip()
    assert ".* build dist venv node_modules __pycache__ data logs ops/runtime" == norecursedirs
