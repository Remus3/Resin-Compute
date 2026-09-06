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
