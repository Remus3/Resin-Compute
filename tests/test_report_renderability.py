"""A failure report must stay renderable while a test has os.name patched.

Several tests in both suites do `monkeypatch.setattr(os, "name", "nt")` to reach
a Windows-only branch (tests/test_hook_gate.py:944, 960, 1002, 1127;
tests/test_hook_interpreter.py:1575, 1635, 1677). pytest builds the failure
report for the call phase while that patch is STILL LIVE:

    _pytest.runner.call_and_report
      -> ihook.pytest_runtest_makereport
      -> TestReport.from_item_and_call
      -> _format_failed_longrepr            (_pytest/reports.py:263)
      -> Node._repr_failure_py              (_pytest/nodes.py:444)

whose first act is `abspath = Path(os.getcwd()) != invocation_params.dir`,
guarded only by `except OSError`. `pathlib.Path` dispatches on `os.name`, so on
a POSIX host that line constructs a `WindowsPath` and raises - and the raise is
not an OSError, so pytest dies with INTERNALERROR instead of naming the failing
test. A failure that cannot be named cannot be fixed.

The repo-root `conftest.py` wraps `pytest_runtest_makereport` to hold `os.name`
at the interpreter's real value for the duration of report construction, then
puts back whatever the test had set so the test's own monkeypatch teardown still
sees what it expects.

HOW THESE ARMS OBSERVE. They run pytest in a SUBPROCESS against a scratch file
under tempfile - never inside the repo - and read `os.name` from INSIDE report
construction using an exception whose `__str__` appends what it sees.
`ExceptionInfo.exconly()` calls `str(exc)` while materialising the longrepr,
which is strictly inner to every hook wrapper, so no wrapper-ordering assumption
is needed. Observations are APPENDED, so a later `str()` call cannot erase an
earlier one.

WHAT THE SCRATCH TEST PATCHES IN. It patches `os.name` to `_FOREIGN_OS_NAME`, a
sentinel chosen so it can never equal the interpreter's real `os.name` on ANY
host. The literal "posix" was hardcoded here until 2026-09-09, chosen as the
inverse of this Windows host's "nt". On Linux "posix" IS the real value, so the
patch was a NO-OP there: the protected and the unprotected run observed the
same string, and the positive control below could not separate its two
conditions at all. It was not merely failing on Linux, it was incapable of
measuring anything, and the Windows green was the accident rather than the
Linux red. `test_the_patched_value_is_foreign_on_every_host` now asserts the
non-equality on every host, at the point of the mistake.

WHY THE SENTINEL IS NOT "nt". `pathlib.Path` selects `WindowsPath` for exactly
the string "nt" and a `PosixPath` for anything else, so patching to "nt" on a
POSIX host is the very crash this file exists to prevent regressing - the
unprotected control would abort the whole run with INTERNALERROR instead of
failing cleanly. Any other string yields a `PosixPath` on Linux and is
harmless. The specific string carries no meaning; the probe only needs the two
observations to DIFFER.

WHAT THESE ARMS CANNOT CLAIM. They do NOT reproduce the crash on this Windows
host: measured on CPython 3.14.4 here, `Path(".")` under a patched `os.name`
returns a `PosixPath` without raising, because `pathlib.Path.__new__` selects
the class and then calls `object.__new__`, bypassing the `PosixPath.__new__`
guard. CPython 3.11 - the version CI pins in .github/workflows/ci.yml, on
ubuntu-latest - raises NotImplementedError from `Path.__new__` itself, but only
for the flavour the running host cannot support, which on Linux is
`WindowsPath` and is never what the sentinel selects. So these arms grade the
MECHANISM (os.name is held at its real value during report construction and put
back afterwards), not the Linux crash. The Linux behaviour is UNVERIFIED on
this box.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_CONFTEST = REPO_ROOT / "conftest.py"

# No -q, no addopts inherited from the repo's pytest.ini: the scratch run needs
# its own summary line and its own rootdir.
_PYTEST_INI = b"[pytest]\naddopts =\n"

# The value the scratch test patches os.name to. It must differ from the real
# os.name on EVERY host and must not be "nt" - see the module docstring for both
# reasons. test_the_patched_value_is_foreign_on_every_host guards it.
_FOREIGN_OS_NAME = "resincompute-foreign-os-name"

_SCRATCH_TEST_TEMPLATE = b'''\
import os
import pathlib

_LOG = pathlib.Path(__file__).with_name("observed.txt")


def _append(tag):
    with open(str(_LOG), "a", encoding="ascii", newline="\\n") as handle:
        handle.write(tag + "\\n")


class ReportProbe(AssertionError):
    """__str__ runs inside report construction, inner to every hook wrapper."""

    def __str__(self):
        _append("report:" + os.name)
        return "report probe fired"


def test_renderability_probe(monkeypatch, request):
    monkeypatch.setattr(os, "name", "@FOREIGN_OS_NAME@")
    # Registered DURING the test body, so it is later than the monkeypatch
    # fixture's own finalizer and - finalizers being LIFO - runs BEFORE
    # monkeypatch.undo. Measured 2026-09-09: an autouse fixture's post-yield
    # code runs AFTER monkeypatch.undo here and therefore always reads the
    # real os.name, which makes it useless as a put-back probe.
    request.addfinalizer(lambda: _append("teardown:" + os.name))
    raise ReportProbe()
'''

_SCRATCH_TEST = _SCRATCH_TEST_TEMPLATE.replace(
    b"@FOREIGN_OS_NAME@", _FOREIGN_OS_NAME.encode("ascii")
)

# Control A: no hook at all. This is what the tree looked like before the fix,
# and it is the arm that proves the probe can tell protected from unprotected.
_CONFTEST_UNPROTECTED = b'"""Control: no makereport hook."""\n'

# Control B: a mutant that restores the real os.name but never puts the test's
# value back. Non-vacuity for the second half of the contract.
_CONFTEST_NO_PUTBACK = b'''\
"""Mutant control: restores os.name for the report and never puts it back."""
import os

import pytest

_REAL_OS_NAME = os.name


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    os.name = _REAL_OS_NAME
    return (yield)
'''


def _run_case(tmpdir: Path, conftest_bytes: bytes) -> tuple[int, str, list[str]]:
    """Write a scratch package, run pytest on it, return rc, stdout, log lines."""
    (tmpdir / "pytest.ini").write_bytes(_PYTEST_INI)
    (tmpdir / "conftest.py").write_bytes(conftest_bytes)
    (tmpdir / "test_scratch.py").write_bytes(_SCRATCH_TEST)

    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_CURRENT_TEST", None)
    # A net-zero mutate-and-restore inside one second runs stale bytecode; the
    # scratch conftests differ in length AND no bytecode is written at all.
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "test_scratch.py",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(tmpdir),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    log = tmpdir / "observed.txt"
    lines = log.read_text(encoding="ascii").splitlines() if log.exists() else []
    return proc.returncode, proc.stdout + proc.stderr, lines


def _protected() -> tuple[int, str, list[str]]:
    with tempfile.TemporaryDirectory() as raw:
        return _run_case(Path(raw), ROOT_CONFTEST.read_bytes())


def test_the_patched_value_is_foreign_on_every_host() -> None:
    """LOUD GUARD: what the arms patch in is never the interpreter's os.name.

    Hardcoding "posix" here made every arm below a no-op on Linux, where it is
    the REAL value: the patched and the real observation were the same string,
    so the positive control could not distinguish its two conditions and
    asserted nothing at all. This single arm fails on the host that has the
    problem, instead of surfacing as a confusing red through a CI round trip.
    """
    assert _FOREIGN_OS_NAME != os.name, (
        f"the scratch test patches os.name to {_FOREIGN_OS_NAME!r}, which IS this "
        "interpreter's real os.name, so the arms below cannot distinguish a "
        "protected run from an unprotected one"
    )
    # Pin against the whole closed set of real os.name values, not just this
    # host's. "posix" satisfied the check above on Windows and still broke
    # Linux, so a this-host-only check is exactly the blind spot being closed.
    # "nt" is doubly excluded: pathlib.Path selects WindowsPath for exactly that
    # string, which raises from Path.__new__ on a POSIX host under CPython 3.11
    # and would abort the unprotected control with INTERNALERROR.
    assert _FOREIGN_OS_NAME not in {"nt", "posix", "java"}, (
        f"{_FOREIGN_OS_NAME!r} is a real os.name value on some host, so this file "
        "is platform-blind again"
    )
    # NON-VACUITY: the sentinel must actually reach the scratch source. A lost
    # placeholder would ship the template unsubstituted and silently patch
    # os.name to the literal string "@FOREIGN_OS_NAME@" instead.
    assert _FOREIGN_OS_NAME.encode("ascii") in _SCRATCH_TEST, _SCRATCH_TEST
    assert b"@FOREIGN_OS_NAME@" not in _SCRATCH_TEST, "placeholder never substituted"
    assert b"@FOREIGN_OS_NAME@" in _SCRATCH_TEST_TEMPLATE, "template lost its placeholder"


def test_root_conftest_is_the_artifact_under_test() -> None:
    """The protected case must run the repo's real conftest bytes, not a copy."""
    assert ROOT_CONFTEST.is_file(), f"missing {ROOT_CONFTEST}"
    body = ROOT_CONFTEST.read_bytes()
    assert b"pytest_runtest_makereport" in body
    # The pre-existing claim of that module must survive.
    assert b"sys.path.insert" in body


def test_report_construction_sees_the_real_os_name() -> None:
    """With the root conftest's hook, report construction sees the real os.name."""
    _rc, _out, lines = _protected()
    observed = [ln for ln in lines if ln.startswith("report:")]
    assert observed, f"probe never fired during report construction: {lines}"
    assert f"report:{os.name}" in observed, (
        f"report construction never saw the real os.name {os.name!r}; saw {observed}"
    )


def test_unprotected_control_sees_the_patched_os_name() -> None:
    """POSITIVE CONTROL: without the hook the probe records the patched value.

    If this arm ever passes alongside the protected arm without a difference,
    the probe is measuring nothing.
    """
    with tempfile.TemporaryDirectory() as raw:
        _rc, _out, lines = _run_case(Path(raw), _CONFTEST_UNPROTECTED)
    observed = [ln for ln in lines if ln.startswith("report:")]
    assert observed, f"probe never fired during report construction: {lines}"
    assert f"report:{os.name}" not in observed, (
        "the unprotected control saw the real os.name, so the probe cannot "
        f"distinguish a protected run from an unprotected one; saw {observed}"
    )
    # str(exc) is called more than once while the longrepr is built; what
    # matters is that NO observation is the real os.name.
    assert set(observed) == {f"report:{_FOREIGN_OS_NAME}"}, observed


def test_hook_puts_the_tests_own_os_name_back() -> None:
    """After the report, os.name is whatever the test set, for its teardown."""
    _rc, _out, lines = _protected()
    teardown = [ln for ln in lines if ln.startswith("teardown:")]
    assert teardown == [f"teardown:{_FOREIGN_OS_NAME}"], (
        f"the test's own os.name was not put back for teardown; saw {teardown}"
    )


def test_no_putback_mutant_is_caught() -> None:
    """NON-VACUITY: a hook that never puts the value back is visible here."""
    with tempfile.TemporaryDirectory() as raw:
        _rc, _out, lines = _run_case(Path(raw), _CONFTEST_NO_PUTBACK)
    teardown = [ln for ln in lines if ln.startswith("teardown:")]
    assert teardown == [f"teardown:{os.name}"], (
        "the mutant control did not leak the real os.name into teardown, so "
        f"the put-back arm above is asserting nothing; saw {teardown}"
    )


def test_failing_test_is_named_and_no_internalerror() -> None:
    """The stated success criterion, asserted against the protected run.

    On this Windows host neither run INTERNALERRORs, so this arm cannot
    discriminate here - it is the regression tripwire for a POSIX host and for
    any future pytest whose report path becomes strict about os.name.
    """
    rc, out, _lines = _protected()
    assert "INTERNALERROR" not in out, out
    assert "test_scratch.py::test_renderability_probe" in out, out
    assert rc == 1, f"expected the scratch test to FAIL, got rc={rc}\n{out}"
