"""An empty parametrize list must FAIL at collection, never skip.

pytest's default for ``empty_parameter_set_mark`` is ``skip``: a
``@pytest.mark.parametrize`` whose argument list has gone empty - a corpus
built from ``git ls-files`` that matched nothing, a table that a refactor
emptied - collects as one SKIPPED item and the run stays green. That is a
guard silently testing nothing. ``pytest.ini`` therefore pins
``empty_parameter_set_mark = fail_at_collect``.

Three arms:

* the ini arm reads ``pytest.ini`` with ``configparser`` and asserts the key;
* the probe arm writes a one-test module with an empty parametrize into
  ``tmp_path`` and runs a CHILD pytest against THIS repo's ``pytest.ini``,
  asserting a non-zero exit and pytest's own collect-time message;
* the control arm runs the same probe with the option overridden back to
  ``skip`` and asserts it passes with a skip - the non-vacuity arm proving the
  probe can tell the two policies apart rather than failing for some other
  reason.

The message literal is pytest's own, from ``_pytest/mark/structures.py``
(``get_empty_parameterset_mark``), pytest 9.0.3.
"""

from __future__ import annotations

import configparser
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTEST_INI = REPO_ROOT / "pytest.ini"

# Launched by sys.executable, never a bare name - see CLAUDE.md.
_PYTEST = (sys.executable, "-m", "pytest")

_FAIL_MESSAGE = "Empty parameter set in 'test_probe'"

_PROBE_SOURCE = (
    "import pytest\n"
    "\n"
    "\n"
    "@pytest.mark.parametrize(\"value\", [])\n"
    "def test_probe(value):\n"
    "    assert value\n"
)


def _child_env() -> dict[str, str]:
    # Strip every PYTEST_* variable so the parent's PYTEST_ADDOPTS (or a
    # plugin autoload setting) cannot change the child's policy.
    return {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTEST_")}


def _run_probe(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    probe = tmp_path / "test_empty_probe.py"
    probe.write_bytes(_PROBE_SOURCE.encode("ascii"))
    cmd = [
        *_PYTEST,
        "-c",
        str(PYTEST_INI),
        "--rootdir",
        str(tmp_path),
        "-p",
        "no:cacheprovider",
        "-rs",
        *extra,
        str(probe),
    ]
    return subprocess.run(
        cmd,
        cwd=tmp_path,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_pytest_ini_pins_empty_parameter_set_mark_to_fail_at_collect() -> None:
    parser = configparser.ConfigParser(interpolation=None)
    with PYTEST_INI.open(encoding="ascii") as fh:
        parser.read_file(fh)
    assert parser.has_section("pytest"), "pytest.ini has no [pytest] section"
    value = parser.get("pytest", "empty_parameter_set_mark", fallback=None)
    assert value is not None, "pytest.ini does not set empty_parameter_set_mark"
    assert value.strip() == "fail_at_collect", value


def test_an_empty_parametrize_fails_at_collection_under_the_repo_ini(
    tmp_path: Path,
) -> None:
    proc = _run_probe(tmp_path)
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0, output
    assert _FAIL_MESSAGE in output, output
    assert "1 skipped" not in output, output


def test_control_the_probe_skips_when_the_policy_is_overridden_to_skip(
    tmp_path: Path,
) -> None:
    # Non-vacuity: the same probe, same ini, with only the policy flipped back
    # to pytest's default. If this arm failed too, the probe arm above would
    # be red for a reason other than the policy.
    proc = _run_probe(tmp_path, "-o", "empty_parameter_set_mark=skip")
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, output
    assert "1 skipped" in output, output
    assert "got empty parameter set" in output, output
    assert _FAIL_MESSAGE not in output, output
