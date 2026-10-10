"""Kit budget refusals that are NOT a spent budget get their own terminations.

RSC-NEXT-SESSION item 2: the kit's "budget lock unopenable" and "budget write
failed" refusals (ops/fleet_kit/fleet_headless.py, `code="budget-lock-unopenable"`
and `code="budget-write-failed"`) used to fall through the responder's
"budget" substring match to `KitRunBudgetSpent`, so the log read a full run
cap when the kit's record was merely unopenable or unwritable. They now map
by the kit's `Refused.code` to their own `NoSessionStarted` subclasses.

Each arm raises the refusal with the EXACT text and code the kit raises, so a
kit that renames either code fails here rather than silently re-reading as a
spent budget. The neighbours that must survive - a spent budget and a busy
lock - are pinned beside them.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools" / "moon_sync_responder.py"
KIT_SOURCE = ROOT / "ops" / "fleet_kit" / "fleet_headless.py"

#: Absolute, outside the repo, and never executed: `kit.spawn` is stubbed.
FAKE_EXE = Path(os.path.abspath(os.sep)) / "fake-bin-never-run" / "claude.exe"


@pytest.fixture()
def rsp(tmp_path):
    """The responder with every `DEFAULT_*` path redirected into `tmp_path`."""
    spec = importlib.util.spec_from_file_location("responder_budget_codes_under_test", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


@pytest.fixture()
def refusing(rsp, monkeypatch, tmp_path):
    """Route `_spawn_headless` up to `kit.spawn`, which raises what the arm sets."""
    kit = rsp.kit
    monkeypatch.setattr(rsp, "KIT_ROOT", tmp_path / "kitroot")
    monkeypatch.setattr(kit, "check_url", lambda *_a, **_k: ("127.0.0.1", 9))
    monkeypatch.setattr(kit, "probe", lambda *_a, **_k: None)
    monkeypatch.setattr(rsp, "_claude_exe", lambda: str(FAKE_EXE))
    box: dict[str, BaseException] = {}

    def spawn(*_a, **_k):
        raise box["exc"]

    monkeypatch.setattr(kit, "spawn", spawn)

    def arm(exc: BaseException) -> BaseException:
        box["exc"] = exc
        with pytest.raises(rsp.SpawnFailed) as caught:
            rsp._spawn_headless("p", rsp.Bounds())
        return caught.value

    return arm


#: (kit text, kit code, responder class name, termination). The text and code
#: are the kit's own, as `test_the_kit_still_raises_these_codes` re-reads them.
FAULTS = (
    ("budget lock unopenable: PermissionError", "budget-lock-unopenable",
     "KitBudgetLockUnopenable", "kit-budget-lock-unopenable"),
    ("budget write failed: OSError", "budget-write-failed",
     "KitBudgetWriteFailed", "kit-budget-write-failed"),
)


def test_the_kit_still_raises_these_codes():
    """Non-vacuity of the arms below: the codes are the kit's, not invented here."""
    text = KIT_SOURCE.read_text(encoding="utf-8")
    for code in ("budget-lock-unopenable", "budget-write-failed", "budget-lock-busy", "budget-spent"):
        assert f'code="{code}"' in text, code


@pytest.mark.parametrize(("why", "code", "cls_name", "termination"), FAULTS)
def test_a_budget_record_fault_has_its_own_termination(rsp, refusing, why, code, cls_name, termination):
    exc = refusing(rsp.kit.Refused(why, code=code))
    assert not isinstance(exc, rsp.KitRunBudgetSpent), f"a record fault is not a spent budget: {exc!r}"
    cls = getattr(rsp, cls_name)
    assert type(exc) is cls, type(exc)
    assert issubclass(cls, rsp.NoSessionStarted)
    assert exc.termination == termination
    assert termination in rsp.TERMINATIONS
    assert str(exc) == why


@pytest.mark.parametrize(("_why", "_code", "_cls", "termination"), FAULTS)
def test_a_budget_record_fault_reads_as_a_backoff_not_a_limit(rsp, _why, _code, _cls, termination):
    """Fail closed and retry next tick, like `KitBudgetUnreadable`: never "limit"."""
    assert rsp._TICK_STATES[termination] == rsp._TICK_STATES["usage-backoff"]


def test_the_two_fault_terminations_are_distinct(rsp):
    names = [t for *_x, t in FAULTS]
    assert len(set(names)) == 2
    for name in names:
        assert name not in ("kit-run-budget", "run-locked", "usage-backoff")
        assert name not in rsp.WORK_ATTEMPT_TERMINATIONS


def test_neighbour_a_spent_kit_budget_is_still_kit_run_budget(rsp, refusing):
    exc = refusing(rsp.kit.Refused("run budget exhausted (120/120)", code="budget-spent"))
    assert type(exc) is rsp.KitRunBudgetSpent and exc.termination == "kit-run-budget"


def test_neighbour_a_busy_kit_lock_is_still_run_locked(rsp, refusing):
    exc = refusing(rsp.kit.Refused("budget lock busy", code="budget-lock-busy"))
    assert type(exc) is rsp.KitBudgetLockBusy and exc.termination == "run-locked"


def test_neighbour_a_route_refusal_is_still_headless_refused(rsp, refusing):
    exc = refusing(rsp.kit.Refused("halt file present"))
    assert type(exc) is rsp.HeadlessRefused


# --- item 0m: the busy lock maps by the kit's CODE, not by its message text ---

#: The kit's one raise of the busy refusal, byte-exact (v15,
#: `ops/fleet_kit/fleet_headless.py`, `RunBudget._lock`).
KIT_BUSY_RAISE = 'raise Refused("budget lock busy", code="budget-lock-busy")'


def test_the_kit_raises_the_busy_lock_only_with_its_code():
    """Every kit site carrying the busy text carries the code with it, so the
    responder's code lookup sees every busy refusal the kit can raise."""
    text = KIT_SOURCE.read_text(encoding="utf-8")
    assert text.count(KIT_BUSY_RAISE) == 1, "the kit's busy raise moved or changed"
    assert text.count('"budget lock busy"') == text.count(KIT_BUSY_RAISE)


def test_the_busy_code_is_in_the_responder_code_table(rsp):
    assert rsp._KIT_REFUSAL_BY_CODE.get("budget-lock-busy") is rsp.KitBudgetLockBusy


@pytest.mark.parametrize("why", ["lock contended past its wait", "busy"])
def test_a_busy_code_with_other_text_is_still_run_locked(rsp, refusing, why):
    """The code decides, not the message: a reworded kit text stays Idle."""
    exc = refusing(rsp.kit.Refused(why, code="budget-lock-busy"))
    assert type(exc) is rsp.KitBudgetLockBusy and exc.termination == "run-locked"
    assert str(exc) == why


def test_a_busy_code_beats_a_budget_spent_text(rsp, refusing):
    """Non-vacuity of the code lookup: this text alone reads as a spent budget."""
    why = "run budget exhausted (120/120)"
    assert type(refusing(rsp.kit.Refused(why))) is rsp.KitRunBudgetSpent
    exc = refusing(rsp.kit.Refused(why, code="budget-lock-busy"))
    assert type(exc) is rsp.KitBudgetLockBusy and exc.termination == "run-locked"


def test_the_busy_text_without_its_code_no_longer_decides(rsp, refusing):
    """Item 0m: the busy lock maps by CODE only. A codeless "budget lock busy"
    (the v15 kit never raises one) falls through to the generic "budget"
    text match like any other codeless budget refusal."""
    exc = refusing(rsp.kit.Refused("budget lock busy"))
    assert type(exc) is rsp.KitRunBudgetSpent
