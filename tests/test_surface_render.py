"""Tests for the dashboard renderer and the HTTP surface.

THE ONE THAT MATTERS MOST IS THE ESCAPING TEST. A character's display name
arrives from `enka.network` - it is a nickname another player typed, carried
through `MappedCharacter.display_name` into this page. Interpolating it into
HTML unescaped is a stored cross-site scripting hole with an external author,
and the page runs inside an Electron window. It is escaped, and it is tested.

The renderer is a pure function of a `Dashboard`, so everything here is graded
without a socket. The server tests use a real loopback bind on an ephemeral port
rather than the reserved one, so running the suite never contends with a
dashboard the operator has open.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime

import pytest

from core.types import AccountState, MappedCharacter
from surface.model import Dashboard, Panel, PanelState, build_dashboard
from surface.render import render_html, render_json
from surface.server import DashboardServer

NOW = datetime(2026, 9, 6, 19, 30, tzinfo=UTC)


def board() -> Dashboard:
    return build_dashboard(AccountState(uid="000000000"), now=NOW)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_render_html_produces_a_whole_document():
    html = render_html(board())
    assert html.startswith("<!doctype html>")
    assert "</html>" in html


def test_every_panel_title_reaches_the_page():
    page = render_html(board())
    for panel in board().panels:
        assert panel.title in page


def test_a_not_wired_panel_renders_what_it_is_waiting_on():
    page = render_html(board())
    teams = board().panel("teams")
    assert teams.waiting_on[:40] in page


def test_the_readiness_summary_is_on_the_page():
    page = render_html(board())
    assert "readiness" in page.lower()


def test_the_page_is_seven_bit_ascii():
    """The tree is 7-bit ASCII by hard rule, and this page is authored text."""
    page = render_html(board())
    assert page.isascii(), "the rendered page carries a non-ASCII character"


def test_an_externally_supplied_display_name_is_folded_to_seven_bit_ascii():
    """The OTHER half of the ASCII claim, and the half that was not graded.

    `test_the_page_is_seven_bit_ascii` above renders the `board()` fixture,
    whose roster is empty - so every byte it measures is text THIS repository
    authored, and it cannot see a defect in how an EXTERNALLY supplied name is
    rendered. `html.escape` closes the markup hole and passes every non-ASCII
    codepoint straight through, so a real nickname carrying an em-dash put the
    page outside 7-bit ASCII while that arm stayed green on both sides of it.
    `render_json` never had the hole because it uses `ensure_ascii=True`.

    The glyphs are built with `chr()` and never typed. An em-dash literal here
    would make the file violate the very rule it exists to enforce, and
    `tools/precommit_gate.py` would reject it.

    SURVIVAL IS ASSERTED, NOT JUST ASCII-NESS. Dropping the name entirely would
    also satisfy `isascii()` and would be a worse outcome than the bug, so the
    numeric character references `xmlcharrefreplace` emits are pinned in order.
    """
    em_dash = chr(0x2014)
    en_dash = chr(0x2013)
    smart_quote = chr(0x2019)
    cjk = chr(0x4E2D)
    nbsp = chr(0x00A0)
    glyphs = (em_dash, en_dash, smart_quote, nbsp, cjk)
    display_name = "Ayaka" + "".join(glyphs)

    state = AccountState(uid="000000000")
    state.roster = (
        MappedCharacter(
            avatar_id=10000002,
            level=90,
            ascension=6,
            constellations=0,
            display_name=display_name,
        ),
    )
    page = render_html(build_dashboard(state, now=NOW))

    offenders = sorted({hex(ord(ch)) for ch in page if not ch.isascii()})
    assert page.isascii(), f"externally supplied name left the page non-ASCII: {offenders}"
    expected = "Ayaka" + "".join(f"&#{ord(ch)};" for ch in glyphs)
    assert expected in page, "the name was dropped rather than encoded: " + expected


def test_an_externally_supplied_display_name_is_escaped():
    """The XSS test. `display_name` originates with another player's nickname."""
    state = AccountState(uid="000000000")
    state.roster = (
        MappedCharacter(
            avatar_id=10000096,
            level=60,
            ascension=3,
            constellations=0,
            display_name="<script>alert('x')</script>",
        ),
    )
    page = render_html(build_dashboard(state, now=NOW))
    assert "<script>alert" not in page
    assert "&lt;script&gt;" in page


def test_a_hostile_name_cannot_break_out_of_an_attribute():
    state = AccountState(uid="000000000")
    state.roster = (
        MappedCharacter(
            avatar_id=10000096,
            level=1,
            ascension=0,
            constellations=0,
            display_name='" onmouseover="alert(1)',
        ),
    )
    page = render_html(build_dashboard(state, now=NOW))
    assert 'onmouseover="alert(1)"' not in page


def test_render_json_round_trips_and_names_every_panel():
    payload = json.loads(render_json(board()))
    assert payload["schema"] == 1
    assert {p["panel_id"] for p in payload["panels"]} == set(
        p.panel_id for p in board().panels
    )
    assert 0.0 <= payload["readiness"] <= 1.0


def test_render_json_states_are_the_declared_vocabulary():
    payload = json.loads(render_json(board()))
    allowed = {s.value for s in PanelState}
    assert {p["state"] for p in payload["panels"]} <= allowed


def test_rendering_a_degraded_panel_never_leaks_a_traceback():
    panel = Panel(
        panel_id="x",
        title="X",
        state=PanelState.PARTIAL,
        waiting_on="This panel could not be built from the current state.",
    )
    page = render_html(Dashboard(generated_at=NOW, panels=(panel,)))
    assert "Traceback" not in page
    assert "File \"" not in page


# ---------------------------------------------------------------------------
# The HTTP surface
# ---------------------------------------------------------------------------


@pytest.fixture()
def running_server():
    """Bind an EPHEMERAL port, never the reserved one.

    Running the suite must not contend with a dashboard the operator has open,
    and a test that binds a fixed port fails for a reason that has nothing to do
    with the code under test.
    """
    server = DashboardServer(host="127.0.0.1", port=0, state_provider=lambda: AccountState(uid="000000000"))
    server.start()
    try:
        yield server
    finally:
        server.stop()


def _get(server: DashboardServer, path: str):
    with urllib.request.urlopen(f"{server.base_url}{path}", timeout=5) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read().decode("utf-8")


def test_the_server_binds_loopback_only(running_server):
    assert running_server.host == "127.0.0.1"
    assert running_server.port != 0


def test_the_index_route_serves_the_dashboard(running_server):
    status, content_type, body = _get(running_server, "/")
    assert status == 200
    assert "text/html" in content_type
    assert "<!doctype html>" in body


def test_the_health_route_reports_alive(running_server):
    status, content_type, body = _get(running_server, "/health")
    assert status == 200
    assert "application/json" in content_type
    payload = json.loads(body)
    assert payload["status"] == "ok"
    assert isinstance(payload["pid"], int)


def test_the_json_route_serves_the_same_board(running_server):
    status, _, body = _get(running_server, "/api/dashboard")
    assert status == 200
    payload = json.loads(body)
    assert payload["panels"]


def test_an_unknown_route_is_a_friendly_404_not_a_stack_trace(running_server):
    with pytest.raises(urllib.error.HTTPError) as caught:
        _get(running_server, "/no/such/route")
    assert caught.value.code == 404
    body = caught.value.read().decode("utf-8")
    assert "Traceback" not in body


def test_a_failing_state_provider_degrades_rather_than_500s():
    """The hard rule at the HTTP boundary.

    A provider that raises must not hand the operator a stack trace, and must not
    take the window to a blank page.
    """
    def boom():
        raise RuntimeError("synthetic provider failure")

    server = DashboardServer(host="127.0.0.1", port=0, state_provider=boom)
    server.start()
    try:
        status, _, body = _get(server, "/")
        assert status == 200
        assert "Traceback" not in body
        assert "synthetic provider failure" not in body
    finally:
        server.stop()


def test_the_server_sets_a_restrictive_content_security_policy(running_server):
    """The page runs inside an Electron window, so its CSP is load bearing."""
    with urllib.request.urlopen(f"{running_server.base_url}/", timeout=5) as response:
        csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src" in csp
    assert "'self'" in csp


def test_the_page_loads_no_remote_resource(running_server):
    """No CDN, no font host, no analytics. Everything is inline and local."""
    _, _, body = _get(running_server, "/")
    remote = re.findall(r'(?:src|href)\s*=\s*"(https?://[^"]+)"', body)
    assert remote == []


# ---------------------------------------------------------------------------
# The invisible drag strip
# ---------------------------------------------------------------------------


def test_the_page_carries_an_invisible_drag_strip():
    """The window is frameless, so this strip is the ONLY way to move it.

    Without a title bar the operating system draws nothing to grab, and a
    companion pinned above a fullscreen game that cannot be repositioned is one
    the operator stops using. So its presence is pinned rather than assumed.
    """
    page = render_html(board())
    assert '<div id="dragbar"></div>' in page
    assert "#dragbar" in page


def test_the_drag_strip_is_transparent_and_spans_the_full_width():
    page = render_html(board())
    block = page.split("#dragbar {", 1)[1].split("}", 1)[0]
    assert "position: fixed" in block
    assert "top: 0" in block
    assert "left: 0" in block
    assert "right: 0" in block
    assert "background: transparent" in block
    assert "-webkit-app-region: drag" in block


def test_the_drag_strip_sits_above_the_header_it_covers():
    """It has to win the event, or only the gaps between words would drag."""
    page = render_html(board())
    drag_block = page.split("#dragbar {", 1)[1].split("}", 1)[0]
    drag_z = int(drag_block.split("z-index:", 1)[1].split(";", 1)[0].strip())

    nodrag_block = page.split(".no-drag {", 1)[1].split("}", 1)[0]
    nodrag_z = int(nodrag_block.split("z-index:", 1)[1].split(";", 1)[0].strip())

    # The opt-out must outrank the strip, or an element marked no-drag would
    # still be underneath it and would still lose the click.
    assert nodrag_z > drag_z


def test_an_opt_out_class_exists_for_anything_clickable_under_the_strip():
    page = render_html(board())
    assert ".no-drag" in page
    block = page.split(".no-drag {", 1)[1].split("}", 1)[0]
    assert "-webkit-app-region: no-drag" in block


def test_the_drag_strip_appears_before_any_content():
    """It is fixed-position, but DOM order still decides paint order among peers."""
    page = render_html(board())
    assert page.index('id="dragbar"') < page.index("<header>")


# ---------------------------------------------------------------------------
# Freshness on the page, and the snapshot the surface loads
# ---------------------------------------------------------------------------


def test_the_freshness_is_rendered_on_the_page():
    page = render_html(board())
    assert "no reading yet" in page


def test_a_stale_reading_is_marked_stale_on_the_page():
    from datetime import timedelta

    state = AccountState(uid="1")
    state.last_synced_at = NOW - timedelta(days=2)
    page = render_html(build_dashboard(state, now=NOW))
    assert "stale" in page.lower()
    assert "2d" in page


def test_a_fresh_reading_is_not_marked_stale():
    from datetime import timedelta

    state = AccountState(uid="1")
    state.last_synced_at = NOW - timedelta(minutes=3)
    page = render_html(build_dashboard(state, now=NOW))
    assert "3m" in page
    # NOT `"state-stale" not in page`: the class is DEFINED in the stylesheet on
    # every render, so its mere presence says nothing about whether it was
    # applied. The applied form is what distinguishes the two states.
    assert 'class="freshness state-stale"' not in page
    assert "(stale)" not in page


def test_the_json_payload_carries_the_freshness_too():
    payload = json.loads(render_json(board()))
    assert "freshness" in payload
    assert payload["is_stale"] is False


def test_the_default_provider_returns_an_empty_account_with_no_snapshot(tmp_path, monkeypatch):
    from surface.server import default_state_provider

    monkeypatch.setenv("RC_DATA_DIR", str(tmp_path))
    state = default_state_provider()
    assert state.roster == ()
    assert state.last_synced_at is None


def test_the_default_provider_loads_a_snapshot_when_one_exists(tmp_path, monkeypatch):
    """The cold-start path. This is the whole reason persist_state exists."""
    from core.state_io import write_state
    from surface.server import default_state_provider

    monkeypatch.setenv("RC_DATA_DIR", str(tmp_path))
    written = AccountState(uid="618285856", adventure_rank=58)
    written.roster = (
        MappedCharacter(avatar_id=10000096, level=80, ascension=5, constellations=0, display_name="Arlecchino"),
    )
    written.last_synced_at = NOW
    assert write_state(tmp_path / "account_state.json", written)

    state = default_state_provider()
    assert state.uid == "618285856"
    assert state.roster[0].display_name == "Arlecchino"


def test_a_corrupt_snapshot_degrades_to_an_empty_account_rather_than_raising(tmp_path, monkeypatch):
    from surface.server import default_state_provider

    monkeypatch.setenv("RC_DATA_DIR", str(tmp_path))
    (tmp_path / "account_state.json").write_text("{truncated", encoding="utf-8")

    state = default_state_provider()
    assert state.roster == ()


# ---------------------------------------------------------------------------
# Exclusive bind
# ---------------------------------------------------------------------------


def test_a_second_server_cannot_bind_a_port_the_first_already_holds():
    """MEASURED DEFECT, not a hypothetical.

    `ThreadingHTTPServer.allow_reuse_address` is True, which on POSIX only
    sidesteps TIME_WAIT but on WINDOWS lets a completely separate process bind a
    port another process is already listening on. Both sockets then sit in
    LISTENING and which one receives a connection is undefined.

    Observed on this machine: two surfaces bound 8791 simultaneously, and the
    older one answered every request, so a freshly started surface serving new
    code was silently ignored while looking perfectly healthy.

    It also silently breaks a documented contract. `surface.server.main` promises
    exit code 2 for "the port it needs is already held by something else", and
    the Electron shell renders its refusal from exactly that code. Without an
    exclusive bind that code can never fire on Windows.
    """
    first = DashboardServer(host="127.0.0.1", port=0)
    first.start()
    try:
        second = DashboardServer(host="127.0.0.1", port=first.port)
        with pytest.raises(OSError):
            second.start()
    finally:
        first.stop()


def test_main_returns_the_documented_exit_code_when_the_port_is_taken():
    """The contract the Electron supervisor reads."""
    from surface.server import main

    holder = DashboardServer(host="127.0.0.1", port=0)
    holder.start()
    try:
        assert main(["--host", "127.0.0.1", "--port", str(holder.port)]) == 2
    finally:
        holder.stop()


def test_a_stopped_server_releases_its_port_immediately():
    """The exclusive bind must not leave the port unusable afterwards.

    TIME_WAIT making a restart fail is the reason `allow_reuse_address` exists at
    all, so turning it off has to be checked for the regression it could cause.

    RETRIED, AND THE RETRY IS THE POINT rather than a papering-over. Dropping
    SO_REUSEADDR made this rebind strict, which introduces a second way for it to
    fail that has nothing to do with TIME_WAIT: the operating system can hand
    that freed ephemeral port to some other process in the gap. Observed once as
    a single unreproducible failure in an otherwise green suite, which is the
    worst kind - it trains people to re-run rather than to look.

    The two causes are distinguishable by their shape. A TIME_WAIT regression
    would fail on EVERY attempt, deterministically; a third party taking one port
    fails on that port and not on a fresh one. So the assertion is "some
    just-released port can be rebound immediately", which is exactly the claim,
    and it stays non-vacuous because a real regression fails all the attempts.
    """
    attempts = 5
    failures: list[str] = []

    for _ in range(attempts):
        first = DashboardServer(host="127.0.0.1", port=0)
        first.start()
        port = first.port
        first.stop()

        second = DashboardServer(host="127.0.0.1", port=port)
        try:
            second.start()
        except OSError as exc:
            failures.append(f"{port}: {exc.__class__.__name__}")
            continue
        try:
            assert second.port == port
            return
        finally:
            second.stop()

    raise AssertionError(
        "a just-released port could not be rebound on any of "
        f"{attempts} attempts, which is a TIME_WAIT regression rather than "
        f"a stolen port: {failures}"
    )
