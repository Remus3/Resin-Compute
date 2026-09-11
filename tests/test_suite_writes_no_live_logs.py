"""Regression: a test run must not write the operator's live day log.

WHAT WAS MEASURED, and how. A snapshot diff of the tree before and after a
suite run is INVALID on this box - an idle 300 second control with no suite
running showed four candidate files changing anyway, this repo's `logs/` among
them, because daemons and other sessions write these trees concurrently. A file
that changed during a run therefore attributes nothing.

What does attribute is an IN-PROCESS tracer: wrap `builtins.open`, `io.open`,
`os.replace` and `os.rename`, and charge BYTES HANDED TO write() to the nodeid
that was executing. It is process-local, so no other writer can contaminate it.
Run against `python -m pytest tests` at 69e4e9d it recorded

    logs/2026-09-11.log   17492 bytes   51 nodeids   12 files

every one of them a real ERROR line produced on purpose by a degradation arm.
The operator greps a day at a time, so their unit of review filled with
synthetic failures that no incident produced.

THE MECHANISM. `core.log_setup.get_logger()` attaches a `logging.FileHandler`
at `core.config.load_config().log_dir / "<today>.log"` and caches it
process-wide on first use.

THE FIX IS AT THE ROOT. `load_config()` already derives `log_dir` from
`RC_LOG_DIR` WHEN USED rather than freezing it into a module constant at
import, so ONE redirection installed in the rootdir `conftest.py` before
collection isolates every present and future logging caller in BOTH suites. A
per-site injection at 51 call sites would need a hand-kept list, and the next
test to log an error would rediscover the defect.

WHAT THESE ARMS ARE, AND WHICH ONE IS THE CONTROL. The first three would all go
green for the wrong reason if logging had simply stopped working, or if the
comparison could never come out the other way. `test_a_logged_error_reaches_the
_redirected_file` proves the writer is still live, and
`test_without_the_redirect_the_path_lands_inside_the_repo` proves the
comparison is capable of the opposite verdict. Neither moves with the fix,
which is what makes them controls.

STATED LIMIT. These arms observe THIS process. A write performed by a CHILD
process - and this tree runs child pytest processes in several guard modules -
is outside their reach, and was outside the tracer's reach too: the traced run
counted 17492 bytes in-process against 19414 bytes on disk, a 1922 byte gap
consistent with child-process logging.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from core.config import load_config
from core.log_setup import get_logger, log_path_for

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Environment variable -> the `core.config.Config` field it redirects.
#:
#: A TABLE rather than a single hardcoded check, so adding the next live path
#: to the conftest redirect is one row here and not a new module. It is also
#: the population the floor below guards: an empty `parametrize` is reported as
#: nothing collected at exit 0, which is a guard that cannot fail.
REDIRECTED_LIVE_PATHS = {
    "RC_LOG_DIR": "log_dir",
}


def _file_handlers(logger: logging.Logger) -> list[logging.FileHandler]:
    return [h for h in logger.handlers if isinstance(h, logging.FileHandler)]


def test_the_redirect_table_is_not_empty() -> None:
    """FLOOR. Emptying the population must redden, not silently collect zero."""
    assert REDIRECTED_LIVE_PATHS, (
        "REDIRECTED_LIVE_PATHS is empty, so every parametrized arm below "
        "collects nothing and reports exit 0 having measured nothing"
    )


@pytest.mark.parametrize(("env_name", "field"), sorted(REDIRECTED_LIVE_PATHS.items()))
def test_every_live_path_field_is_redirected_away_from_the_repo(
    env_name: str, field: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The config field this run actually resolves must sit outside the repo."""
    del monkeypatch  # the live environment is the subject, not a patched one
    value = getattr(load_config(), field)
    assert isinstance(value, Path), f"{field} is {type(value).__name__}, not a Path"
    resolved = value.resolve()
    assert not resolved.is_relative_to(REPO_ROOT), (
        f"{env_name} is not redirected: load_config().{field} resolves to "
        f"{resolved}, inside {REPO_ROOT}. The suite is writing the operator's "
        "live tree. The redirection belongs in the rootdir conftest.py, not at "
        "the call sites."
    )


def test_the_active_file_handler_is_outside_the_repo() -> None:
    """The handler bytes actually reach, not merely the path config reports."""
    logger = get_logger("tests.suite_writes_no_live_logs")
    handlers = _file_handlers(logger)
    assert handlers, (
        "core.log_setup.get_logger attached no FileHandler, so this arm would "
        "pass without observing the writer it exists to observe"
    )
    for handler in handlers:
        target = Path(handler.baseFilename).resolve()
        assert not target.is_relative_to(REPO_ROOT), (
            f"the live file handler writes {target}, inside {REPO_ROOT}"
        )


def test_a_logged_error_reaches_the_redirected_file() -> None:
    """CONTROL. Proves the writer is live, so the arms above are not vacuous.

    An arm that asserts "nothing was written inside the repo" is satisfied
    perfectly by logging having broken. This one fails in that case.
    """
    logger = get_logger("tests.suite_writes_no_live_logs")
    handlers = _file_handlers(logger)
    assert handlers, "no FileHandler to observe"
    target = Path(handlers[0].baseFilename)
    before = target.stat().st_size if target.exists() else 0
    logger.error("suite-writes-no-live-logs probe line")
    for handler in handlers:
        handler.flush()
    after = target.stat().st_size
    assert after > before, (
        f"{target} did not grow ({before} -> {after}), so file logging is not "
        "actually running and the arms above are green for the wrong reason"
    )


def test_without_the_redirect_the_path_lands_inside_the_repo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CONTROL. The comparison must be able to come out the other way.

    With `RC_LOG_DIR` cleared, `log_path_for()` falls back to the repo default.
    If this ever stopped landing inside the repo, the arms above would be
    asserting something no configuration could violate.
    """
    monkeypatch.delenv("RC_LOG_DIR", raising=False)
    fallback = log_path_for().resolve()
    assert fallback.is_relative_to(REPO_ROOT / "logs"), (
        f"the unredirected default is {fallback}, not under {REPO_ROOT / 'logs'}"
    )
