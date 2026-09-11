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


def _esc(text: str) -> str:
    """Escape for HTML AND force the result to 7-bit ASCII.

    TWO HAZARDS, ONE FUNCTION, AND THE SECOND ONE IS THE EASY ONE TO MISS.
    `html.escape` closes the markup hole. It does NOT close the charset hole: it
    passes every non-ASCII codepoint through untouched.

    `MappedCharacter.display_name` is a nickname another player typed into
    Genshin Impact. Nothing upstream constrains it to ASCII, and in practice it
    carries CJK, accented Latin, an em-dash, a smart quote or a decorative star.
    Interpolated raw, those land in the page and the rendered document silently
    leaves 7-bit ASCII - the tree's hard rule - with no error anywhere.

    MEASURED: a two-character roster whose names carried U+2014, U+2019, U+00A0,
    U+2606 and two CJK codepoints put 48 non-ASCII bytes into the page.

    `xmlcharrefreplace` turns each one into a numeric character reference, so the
    byte stream is ASCII while the browser still paints the name the player
    chose. Nothing is lost and nothing is transliterated. This is the same call
    `render_json` already makes as `ensure_ascii=True`, and the two renderers
    disagreeing about it was the defect.

    ORDER MATTERS. Escape first so an ampersand becomes `&amp;`, then encode, or
    the `&` this function itself emits would be double-escaped.
    """
    return escape(text, quote=True).encode("ascii", "xmlcharrefreplace").decode("ascii")


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
  /* MEASURED, and the old value failed. `--cold` paints the NOT WIRED pill -
     10px text AND its 1px border, via `border: 1px solid currentColor`. At
     #5b6577 that pill measured 2.87:1 on `--card` (#191d27), under the 4.5:1
     floor and under even the 3:1 large-text floor, which it does not qualify
     for at 10px. The least legible thing on the board was the badge that says
     a panel is NOT LIVE - the one honesty signal ADR-005 exists to carry.
     #7d8798 measures 4.65:1 on `--card` and 5.12:1 on `--bg`, and stays clearly
     dimmer than `--ink-dim` (6.48:1) so cold still reads as cold. */
  --cold: #7d8798;
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
/* The header WRAPS, and the shell's own minimum is why. `shell/lib/window.js`
   sets `minWidth: 360`. A non-wrapping flex row plus `.meter`'s 190px floor
   measured a 480px header inside a 360px body - 138px of horizontal overflow,
   pushing the readiness meter, the one at-a-glance summary of how much of the
   board is real, off the right edge. Wrapping costs nothing at the 900px
   default, where the measured layout is byte-identical either way. */
header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
}
h1 { font-size: 16px; margin: 0; letter-spacing: 0.04em; }
.sub { color: var(--ink-dim); font-size: 12px; }
.meter {
  margin-left: auto;
  /* `flex-basis` rather than `min-width`, so the meter PREFERS 190px and yields
     instead of forcing the header wider than the window. */
  flex: 1 1 190px;
  min-width: 0;
}
.meter-track {
  height: 6px;
  border-radius: 3px;
  background: var(--card-edge);
  overflow: hidden;
}
.meter-fill { height: 100%; background: var(--accent); }
/* Freshness. The dashboard renders a SNAPSHOT written by the headless lane, not
   a live query, so the age is not decoration - a cached roster shown without one
   is indistinguishable from a live reading. Stale gets a colour because the
   whole point is that it must not be readable as current at a glance. */
.freshness { color: var(--ink-dim); font-size: 12px; }
.state-stale { color: var(--partial); font-weight: 600; }
/* `align-items: start` so a card is as tall as its own content. The default
   `stretch` sizes every card to the tallest in its grid row: measured at the
   900px default, a 6-row Plan card was inflated to 811px to match Teams, and
   the NOT WIRED Wishes card to 188px, leaving hundreds of pixels of empty card.
   A mostly-empty card reads as a panel that failed to load rather than as one
   that has said its piece. */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  align-items: start;
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
/* TWO EQUAL COLUMNS, NOT `auto 1fr`, AND THE OLD VALUE STARVED THE VALUES.
   With `auto` the label track sizes toward max-content, so ONE long label sets
   the width for the whole card and the value track collapses to its own
   min-content. Measured on the live roster at the 900px default: the label
   "Verified seed characters absent" took 173px of a 249px card, leaving 65px
   for every value in the Teams panel - "pyro" broke over three lines, and the
   card grew to 811px inside a 620px window. `minmax(0, 1fr)` twice caps each
   track and lets both wrap; the same board measured 0 starved values, 2 lines
   worst case, and a 622px card. The `minmax(0, ...)` matters: a bare `1fr` has
   an automatic minimum of min-content and would not shrink. */
dl {
  margin: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 3px 12px;
}
/* `overflow-wrap` because `unknown:10000118` is ONE unbreakable token to a
   browser - a colon is not a break opportunity - and it is the single most
   common label on a real roster, where most ids sit outside the verified seed
   set. Without this it overflows its track instead of wrapping. */
dt { color: var(--ink-dim); overflow-wrap: anywhere; }
dd { margin: 0; text-align: right; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
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
        f'<h2>{_esc(panel.title)}'
        f'<span class="pill {state_class}">{_esc(_STATE_LABEL[panel.state])}</span></h2>',
    ]
    if panel.rows:
        parts.append("<dl>")
        for label, value in panel.rows:
            parts.append(f"<dt>{_esc(label)}</dt><dd>{_esc(value)}</dd>")
        parts.append("</dl>")
    if panel.waiting_on:
        parts.append(f'<p class="waiting">{_esc(panel.waiting_on)}</p>')
    if panel.note:
        parts.append(f'<p class="note">{_esc(panel.note)}</p>')
    parts.append("</section>")
    return "".join(parts)


def render_html(board: Dashboard) -> str:
    """The whole page, as one string.

    Returns a complete document rather than a fragment because the Electron shell
    loads it as a top-level URL and there is no template layer above this.
    """
    percent = round(board.readiness * 100)
    generated = _esc(board.generated_at.isoformat(timespec="seconds"))
    freshness = _esc(board.freshness)
    stale_class = " state-stale" if board.is_stale else ""
    if board.is_stale:
        freshness += " (stale)"
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
        f'<span class="freshness{stale_class}">{freshness}</span>'
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
        "freshness": board.freshness,
        "is_stale": board.is_stale,
        "source_age_seconds": (None if board.source_age is None else int(board.source_age.total_seconds())),
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
