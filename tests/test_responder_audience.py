"""Who the responder answers: every channel participant, never itself.

Operator directive 2026-10-02: this tree reads and answers its channel inbox
and acts on what it receives. The pairwise RC-only filter could not satisfy
that, so the audience is every participant by codename. RSC is never on it -
a responder that answered its own notes would loop - and an unknown sender is
still default-deny.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESPONDER_PATH = ROOT / "tools" / "moon_sync_responder.py"

#: The LIVE audience. MAIN 0230 ORDER of 2026-10-05 (SHA-256 MATCH), refined by
#: the MAIN 2305 RULING of 2026-10-07: EW joined, LL retired. LL is NOT deleted -
#: it moves to `RETIRED`, which every send path consults.
PARTICIPANTS = ("CS", "EW", "LW", "MAIN", "RC", "SS")

#: Retired participants. Kept on record, never answered, never routed to.
RETIRED = ("LL",)


@pytest.fixture()
def rsp(tmp_path):
    spec = importlib.util.spec_from_file_location("responder_audience_under_test", RESPONDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in [n for n in dir(module) if n.startswith("DEFAULT_")]:
        value = getattr(module, name)
        if isinstance(value, Path):
            setattr(module, name, tmp_path / "isolated" / name.lower() / value.name)
    return module


def _inbox(tmp_path: Path, senders: tuple[str, ...]) -> Path:
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    for i, code in enumerate(senders):
        name = f"2026-10-02-10{i:02d}-from-{code}-question.md"
        (inbox / name).write_bytes(b"please measure your suite\n")
    return inbox


def _senders(rsp, inbox: Path) -> set[str]:
    return {rsp.sender_of(p.name) for p in rsp.pending(inbox, rsp.OPTED_IN, set())}


def test_the_audience_is_every_participant(rsp):
    assert set(rsp.OPTED_IN) == set(PARTICIPANTS)


def test_main_and_ss_are_now_pending(rsp, tmp_path):
    inbox = _inbox(tmp_path, ("MAIN", "SS"))
    assert _senders(rsp, inbox) == {"MAIN", "SS"}


def test_self_and_unknown_senders_are_never_pending(rsp, tmp_path):
    inbox = _inbox(tmp_path, ("RSC", "ZZ", "RC"))
    assert _senders(rsp, inbox) == {"RC"}, "only the known participant survives"


def test_self_reply_is_impossible_even_if_self_is_listed(rsp, tmp_path):
    """Belt and braces: `pending` drops SELF_CODE whatever the list says."""
    assert rsp.SELF_CODE not in rsp.OPTED_IN
    inbox = _inbox(tmp_path, (rsp.SELF_CODE,))
    assert rsp.pending(inbox, (*rsp.OPTED_IN, rsp.SELF_CODE), set()) == []


def test_the_self_filter_fires_on_a_listed_foreign_code(rsp, tmp_path):
    """Non-vacuity: the same inbox shape IS picked when the code is foreign."""
    inbox = _inbox(tmp_path, ("SS",))
    assert len(rsp.pending(inbox, ("SS",), set())) == 1


def test_the_retired_set_is_exactly_ll_and_disjoint_from_the_live_audience(rsp):
    assert tuple(rsp.RETIRED) == RETIRED
    assert not set(rsp.RETIRED) & set(rsp.OPTED_IN), "a retired code is still answered"


def test_ew_is_pending_and_ll_is_not(rsp, tmp_path):
    """Both halves in one inbox: the joiner is answered, the retiree is not."""
    inbox = _inbox(tmp_path, ("EW", "LL"))
    assert _senders(rsp, inbox) == {"EW"}


def test_a_retired_sender_gets_no_destination_even_with_a_root(rsp, tmp_path):
    """The send-path gate, independent of `pending`.

    The per-host roster keeps LL's root on purpose (delete nothing), so the
    roots map CAN resolve LL. `destinations_for` must still refuse it.
    """
    roots = {"LL": tmp_path / "ll", "EW": tmp_path / "ew"}
    ll_note = tmp_path / "2026-10-08-0100-from-LL-question.md"
    ew_note = tmp_path / "2026-10-08-0101-from-EW-question.md"
    assert rsp.destinations_for(ll_note, roots) == []
    # Non-vacuity: the same shape with a live code DOES route.
    assert rsp.destinations_for(ew_note, roots) == [tmp_path / "ew"]
