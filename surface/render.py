"""Render a `Dashboard` to HTML or JSON. Pure, and the only place markup exists.

WHY THE RENDERER OWNS NO NUMBERS. Every value on the page arrives from
`surface/model.py` already formatted as a string. This module concatenates and
escapes; it never computes, rounds or defaults. A renderer that formatted its own
numbers would be a second place a value could be wrong, and the second place is
always the one nobody tests.

ESCAPING IS NOT OPTIONAL HERE AND THE REASON IS SPECIFIC. `MappedCharacter.
display_name` originates as a nickname another player typed into Genshin Impact,
travels through the enka.network showcase, and lands on this page. The page then
runs inside an Electron window. Interpolating that unescaped is a stored
cross-site scripting hole whose author is a stranger. Every interpolation below
goes through `html.escape(..., quote=True)`, including inside attributes, and
`tests/test_surface_render.py` pins both the element case and the attribute
break-out case.

NO REMOTE RESOURCE, EVER. No CDN, no web font, no analytics. The stylesheet is
inline. This is partly the offline posture the rest of the tree keeps, and partly
that a dashboard which silently fetches from the internet is a dashboard whose
content-security policy cannot be tight.
"""
from __future__ import annotations

import json
from html import escape

from surface.model import Dashboard, Panel, PanelState

__all__ = ["render_html", "render_json", "STYLESHEET"]

#: Milliseconds between automatic refreshes. Slow on purpose: the underlying
#: state changes on a resin timer measured in minutes, so a fast poll would burn
#: CPU to re-render identical text.
REFRESH_MS = 30_000

_STATE_LABEL = {
    PanelState.READY: "live",
    PanelState.PARTIAL: "partial",
    PanelState.NOT_WIRED: "not wired",
}

STYLESHEET = """
:root {
  color-scheme: dark;
  --bg: #10131a;
  --card: #191d27;
  --card-edge: #262c3a;
  --ink: #e8ecf4;
  --ink-dim: #97a1b5;
  --ready: #4ec9a0;
  --partial: #e0b341;
  --cold: #5b6577;
  --accent: #7aa2f7;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 18px;
  background: var(--bg);
  color: var(--ink);
  font: 14px/1.5 "Segoe UI", system-ui, sans-serif;
  -webkit-user-select: none;
  user-select: none;
}
/* THE INVISIBLE DRAG STRIP.
   The window is frameless, so the operating system draws no title bar and there
   is NOTHING to grab. Without this the window can be moved only by the tray, or
   not at all - which on a companion pinned above a game is the difference
   between usable and abandoned.
   It spans the full width at the very top, is completely transparent, and sits
   ABOVE the header so the whole strip drags rather than only the gaps between
   words. Anything that must stay clickable inside it opts out with .no-drag. */
#dragbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 34px;
  z-index: 9999;
  -webkit-app-region: drag;
  background: transparent;
}
/* Opt-out for interactive elements under the strip. An element that needs a
   click must ALSO raise itself above the strip, or the strip keeps the event. */
.no-drag {
  position: relative;
  z-index: 10000;
  -webkit-app-region: no-drag;
}
header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
}
h1 { font-size: 16px; margin: 0; letter-spacing: 0.04em; }
.sub { color: var(--ink-dim); font-size: 12px; }
.meter {
  margin-left: auto;
  min-width: 190px;
}
.meter-track {
  height: 6px;
  border-radius: 3px;
  background: var(--card-edge);
  overflow: hidden;
}
.meter-fill { height: 100%; background: var(--accent); }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}
.card {
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: 8px;
  padding: 12px 14px;
}
.card h2 {
  font-size: 13px;
  margin: 0 0 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: 0.03em;
}
.pill {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid currentColor;
}
.state-ready { color: var(--ready); }
.state-partial { color: var(--partial); }
.state-not_wired { color: var(--cold); }
.card.state-not_wired h2 { color: var(--ink-dim); }
dl { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 3px 12px; }
dt { color: var(--ink-dim); }
dd { margin: 0; text-align: right; font-variant-numeric: tabular-nums; }
.waiting {
  margin: 8px 0 0;
  color: var(--ink-dim);
  font-size: 12px;
  border-left: 2px solid var(--card-edge);
  padding-left: 9px;
}
.note { margin: 8px 0 0; color: var(--ink-dim); font-size: 11px; font-style: italic; }
footer { margin-top: 16px; color: var(--ink-dim); font-size: 11px; }
"""


def _panel_html(panel: Panel) -> str:
    state_class = f"state-{panel.state.value}"
    parts = [
        f'<section class="card {state_class}">',
        f'<h2>{escape(panel.title)}'
        f'<span class="pill {state_class}">{escape(_STATE_LABEL[panel.state])}</span></h2>',
    ]
    if panel.rows:
        parts.append("<dl>")
        for label, value in panel.rows:
            parts.append(f"<dt>{escape(label, quote=True)}</dt><dd>{escape(value, quote=True)}</dd>")
        parts.append("</dl>")
    if panel.waiting_on:
        parts.append(f'<p class="waiting">{escape(panel.waiting_on, quote=True)}</p>')
    if panel.note:
        parts.append(f'<p class="note">{escape(panel.note, quote=True)}</p>')
    parts.append("</section>")
    return "".join(parts)


def render_html(board: Dashboard) -> str:
    """The whole page, as one string.

    Returns a complete document rather than a fragment because the Electron shell
    loads it as a top-level URL and there is no template layer above this.
    """
    percent = round(board.readiness * 100)
    generated = escape(board.generated_at.isoformat(timespec="seconds"), quote=True)
    cards = "".join(_panel_html(panel) for panel in board.panels)

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        "<title>ResinCompute</title>"
        f"<style>{STYLESHEET}</style>"
        "</head><body>"
        '<div id="dragbar"></div>'
        "<header>"
        "<h1>ResinCompute</h1>"
        f'<span class="sub">{generated}</span>'
        '<div class="meter">'
        f'<div class="sub">Readiness {percent}% '
        f"({board.ready_count} live, {board.partial_count} partial, "
        f"{board.not_wired_count} not wired)</div>"
        '<div class="meter-track">'
        f'<div class="meter-fill" style="width:{percent}%"></div>'
        "</div></div>"
        "</header>"
        f'<div class="grid">{cards}</div>'
        "<footer>A panel that is not live says what it is waiting on. "
        "It never shows a placeholder number - see ADR-005.</footer>"
        f"<script>setTimeout(function(){{location.reload();}}, {REFRESH_MS});</script>"
        "</body></html>"
    )


def render_json(board: Dashboard) -> str:
    """The same board as JSON, for anything that is not a browser.

    `ensure_ascii=True` matches `core/atomic_io.py`: this tree is 7-bit ASCII by
    rule, and a player nickname is the one field likely to carry something else.
    """
    payload = {
        "schema": 1,
        "generated_at": board.generated_at.isoformat(timespec="seconds"),
        "readiness": board.readiness,
        "ready_count": board.ready_count,
        "partial_count": board.partial_count,
        "not_wired_count": board.not_wired_count,
        "panels": [
            {
                "panel_id": panel.panel_id,
                "title": panel.title,
                "state": panel.state.value,
                "rows": [list(row) for row in panel.rows],
                "waiting_on": panel.waiting_on,
                "note": panel.note,
            }
            for panel in board.panels
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
