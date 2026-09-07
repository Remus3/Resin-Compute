---
description: The 5-phase visual audit - STRUCTURE, TYPOGRAPHY, HIT-TARGETS, CHARACTER-SET, HIERARCHY - run over the RENDERED companion surface before the commit, by an agent that did not write the page, ending in a byte-exact verdict.
argument-hint: [the surface under audit, e.g. "surface/render.py teams panel"]
---

# /ui-audit - the 5-phase visual audit

Surface under audit: $ARGUMENTS

Run EVERY phase, in order, and report what you OBSERVE for each. A phase with
no findings still gets a line saying so, because a silently skipped phase and a
clean phase look identical in a report.

Three rules govern when and by whom this runs, and none of them is negotiable:

- **It runs BEFORE the commit, never after.** A page that shipped ahead of its
  audit is a process failure to report, not a gap to fill later.
- **Every MUST-FIX is resolved in the SAME slice.** A MUST-FIX deferred to a
  follow-up is a MUST-FIX that ships. If the fix genuinely belongs to another
  slice, the verdict is BLOCKED and the merge waits.
- **Do not audit a page you authored.** Per `CLAUDE.md` "Session default", the
  agent that produced a thing never grades it. Hand the page to a `ui-auditor`
  from `.claude/agents/` that did not write it. Independence here is a
  prompt-level property: it comes from the producer not grading its own work,
  not from a second opinion of any kind.

## The shape, and what was deliberately not ported

This is Sibling-A's 5-phase audit and Sibling-C's lane-4 ritual adapted to
a much smaller surface, not transcribed from either. Four things were dropped on
purpose:

- **No pseudo-screen capture harness.** Sibling-C renders an in-game
  overlay dock at 2560x1440 because it has one. This tree has a single
  companion window over a local dashboard, and a capture harness for a surface
  that does not exist is a harness that goes stale unread.
- **No mock-fixture flag and no fixture corpus.** Over there, 31 JSON fixtures
  are selected by a query-string flag. Here the page is produced by a PURE
  function - `render_html(board)` in `surface/render.py`, from a `Dashboard`
  that `surface/model.py` builds - so a fixture is a constructed object in a
  test, not a file plus a flag. Do not invent a second mechanism.
- **No OCR or computer-vision arm.** Sibling-C's OCR is calibrated to
  game-HUD regions, and pointing it at a dashboard capture measures nothing.
  This tree has no vision module at all, so a claimed OCR pass would be a
  fabricated one.
- **No headless-Chromium snapshot suite.** Worth having eventually. It is a
  whole subsystem, and Node exists in this tree solely for the Electron shell.
  Until then, anything that must survive into CI is pinned as a TEXT assertion
  in `tests/test_surface_render.py`, which is where the drag-strip, escaping,
  ASCII and content-security-policy pins already live.

One naming decision, carried deliberately: Sibling-C calls phase 4 ASCII
and Sibling-A calls it CHARACTER-SET. **Use CHARACTER-SET**, because in this
tree that phase also carries the leak check, and "ASCII" would make the leak arm
look optional. It is not optional - this tree ingests Enka account data.

## When to skip this entirely

Skip it, and say in the report that you skipped it and why:

- **Backend changes.** `core/`, `engines/`, `headless/`, `ingest/`,
  `agents/pity_engine/`, `ops/` - nothing rendered, nothing to audit.
- **Docs changes.** Any `.md`, the ADRs, `ROADMAP.md`, `docs/LEDGER.md`.
- **Version and dependency bumps** that change no markup, no stylesheet and no
  rendered string.

Run it whenever the change reaches a RENDERED surface. In this tree that means
`surface/` - which owns every byte of markup, per the module docstring in
`surface/render.py` - and `shell/`, which owns the Electron window and the tray
menu the operator actually reads. A change to a panel's TEXT is a rendered
change; so is a change to `surface/model.py`, because every string on the page
arrives from there already formatted.

## 0. Establish what you are auditing, and freeze it

- Name the exact files the slice changed, and read them. An audit that does not
  know what changed reports on the whole page and finds the same five things
  every time.
- **Freeze the candidate.** The tree must not be edited while you measure it. A
  page that changes mid-audit makes the verdict a statement about no state at
  all.
- Note what the change was SUPPOSED to do. A phase-5 HIERARCHY finding is only
  meaningful against a stated intent.

## 1. Stand the surface up, and read it text-first

**Start with the runnable QA that already exists. Build on it, do not duplicate
it.**

```
python scripts/qa_companion.py
```

That script binds an EPHEMERAL port and exercises the port block, the
Python-to-JavaScript port contract in `shell/lib/endpoint.js`, the `/`,
`/api/dashboard` and `/health` routes, the friendly 404, the invisible drag
strip, the panel-readiness invariant ADR-005 exists for, the no-placeholder-
numbers invariant, the account snapshot, the Electron runtime and the desktop
shortcut. It also asserts that the SERVED page is ASCII.

- **If the companion QA is red, STOP and fix that first.** A visual audit over a
  broken surface measures nothing.
- When this audit finds something the companion could have caught, EXTEND the
  companion in the same slice. A finding that leaves no guard behind will be
  found again by hand next time.

Then stand up a real browser and read the RENDERED page:

- If a dashboard is already listening, the companion QA says so and names the
  port - point the browser there. Otherwise start one:
  `python -m surface`, or `python -m surface --port 8792` to stay inside the
  block `core/ports.py` reserves without contending with an open companion.
- Open it with `preview_start` (the `url` form, no dev server), then `navigate`.
  `read_page` gives structure and `ref_N` handles; `javascript_tool` gives the
  numbers; `read_console_messages` catches the fetch failures that reach the
  operator as a panel stuck on a loading state.
- **A screenshot that answers a question `getComputedStyle` could have answered
  is a worse measurement, not a more thorough one.** Reserve pixel capture for
  genuine rendered-pixel questions: does a colour band, does a glyph render as a
  glyph, does the window composite legibly over a game.
- For the shell half, `cd shell && node --test` grades the libraries
  (`shell/test/lib.test.js`, `shell/test/tray.test.js`). The audited surface is
  the page loaded INSIDE that window, plus the tray menu `shell/lib/tray.js`
  builds and the geometry `shell/lib/window.js` applies.

## 2. Four measured failure classes, each of which defeats the obvious check

Each of these was MEASURED in a sibling tree, and each one passes the check you
would naturally reach for. They are stated here as rules for that reason.

1. **An undefined CSS custom property fails SILENTLY.** `var(--typo)` naming a
   property no rule defines is invalid at computed-value time, so the
   declaration falls back to the INHERITED value. It greps fine - the token name
   is right there in the source - and it renders wrong. Measured over there:
   `color: var(--bg)` fell back to inherited near-white at 1.9:1 on an amber
   button, on the one state where misreading the control cost most; the correct
   token measured 9.03:1 on the same surface.
   **RULE: ASSERT COMPUTED STYLES, NEVER SOURCE TEXT.** `surface/render.py`
   defines its tokens on `:root` in `STYLESHEET` and uses them through `var()`
   throughout. There is no guard in `tests/` today proving that every `var()`
   names a defined property - **the first slice that adds a token adds that
   guard**, and this audit is where its absence gets reported.
2. **A repaint throws keyboard focus to the body.** An `innerHTML` rebuild
   destroys the focused node, and node identity is useless afterwards because
   the node is gone. Measured over there: a panel rebuilding four times a second
   during an arm countdown made the confirm click unreachable from the keyboard,
   and nothing in the source looked wrong.
   In this tree the page currently refreshes with `location.reload()` on the
   `REFRESH_MS` timer in `surface/render.py`, which replaces the whole document.
   Today the page emits no focusable control, so nothing is lost - which is
   exactly what makes this a trap rather than a defect: **the first interactive
   control added to this page inherits a focus-destroying repaint.**
   **RULE: capture a STABLE KEY off the focused control before the repaint,
   re-find and re-focus by that key after, and return nothing when focus was not
   inside the host so the restore never STEALS focus. Test focus survival ACROSS
   a repaint** - the presence of the code is not the test.
3. **Contrast must be computed on RESOLVED colours.** An `oklch()` declaration
   sitting after a hex sibling wins, so a checker parsing the hex it found by
   grep is checking a value the browser is not using. Resolve through
   `getComputedStyle` first, every time. This tree's tokens are hex today; the
   rule is about the method, not about the current values.
4. **STATE THE PAIR, NEVER THE TOKEN, when claiming a contrast result.** The
   same token measured 4.88:1 on one surface and 3.94:1 on another over there,
   and the qualifier is the part everyone drops. This page has at least two
   grounds - the body background and the card background - so a token like
   `--ink-dim` has at least two pairings and "`--ink-dim` passes AA" is not a
   result. "`--ink-dim` on the card background measures N:1" is.

## 3. STRUCTURE

- Semantic markup: sections are sections, headings are headings, lists are
  lists. A `div` carrying a heading's meaning is invisible to everything that is
  not an eye.
- **Heading order with no skipped levels, and exactly one `h1`.** The page
  header is the `h1`; every panel title is an `h2` under it.
- Landmarks present and correct: a header, the main content region, a footer.
- Every control is bound to a label. An input with placeholder text and no label
  is an unlabelled input.
- No horizontal overflow at the companion's real width. The window is narrow by
  design; a card that forces a sideways scroll is a defect, not a preference.
- A hidden container actually collapses. A bare `display:flex` beats the user
  agent's `[hidden]` rule, and the cluster then never collapses at all - measured
  in a sibling tree, and invisible to a source read.

## 4. TYPOGRAPHY

- Every size, weight and colour comes from a token in `STYLESHEET`, not from an
  ad hoc value at the call site. A one-off px value is a token nobody can change.
- **Verify by COMPUTED value, not by grep** - see failure class 1.
- Nothing below the legible floor. State the floor you measured against and the
  computed size you observed, as a pair.
- Readable line length in the body copy; the waiting-on and note lines are the
  ones that run long.
- **Numeric columns align.** The page already sets `font-variant-numeric:
  tabular-nums` on the value column for this reason; anything new that shows
  numbers in a column inherits that or states why not.
- Truncation is EXPLICIT. A string cut off with no ellipsis and no title reads
  as a shorter string, which is worse than an obviously clipped one.

## 5. HIT-TARGETS

- Every clickable meets the minimum target size. State the size you measured.
- No overlapping targets, and nothing that is reachable only by mouse.
- **A visible focus ring on everything focusable**, and tab order that follows
  visual order. Tab the page yourself; do not infer the order from the markup.
- **The frameless-window trap, specific to this surface.** The companion has no
  title bar, so `#dragbar` is the only way to move the window - which is why
  `scripts/qa_companion.py` fails outright when it is missing. That strip spans
  the full width at the top with a very high stack order, so **anything
  clickable placed under it must opt out with the `no-drag` class AND raise
  itself above the strip**, or the strip silently eats the click. A control that
  looks perfect and does nothing is this page's most likely new defect.
- Re-test interactive behaviour AFTER a refresh cycle, not only on first paint.
  Binding lifetime is invisible to a source-level test: a handler attached once
  to a node that a later repaint replaced is dead code that reads as live code.

## 6. CHARACTER-SET, and the leak check

**The subject is the RENDERED page, including text inserted after load - not the
source.** Read the live document, not the file:

- Scan `document.documentElement.outerHTML` for any code point above 126, and
  scan `document.body.innerText` as well, because attributes and titles render
  too. Report the offending code point and where it is, so the finding is
  actionable rather than merely a refusal.
- `scripts/qa_companion.py` already asserts the SERVED page is ASCII, and
  `tests/test_surface_render.py` pins it. Neither can see text a script inserts
  later, and neither sees the Electron chrome - the tray labels in
  `shell/lib/tray.js` are rendered text that no page-level check reaches. Those
  are this phase's job.
- The rule reaches the whole authored surface, so `tools/precommit_gate.py`
  stays the backstop for the files themselves:
  `python tools/precommit_gate.py --scan-files <the changed files>`.

**The leak check, and it is load-bearing here because this tree ingests Enka
account data.** Nothing rendered may carry:

- **A Windows account name or a home path.** Both precedents in this tree are
  deliberate and both are worth reading: `surface/server.py` discards the
  child process's OUTPUT and keeps only the exit code, because a message can
  name a path and a path carries the account name; `scripts/qa_companion.py`
  names the shortcut FILE and never its directory, for the same reason.
- **A machine name.** Check the hostname the browser reports and search the
  rendered page for it.
- **A UID.** `ingest/enka_client.py` defines a UID-shaped token as a digit run
  of 6 to 12 characters, so search the rendered text for one and account for
  every hit you find.

A player nickname is NOT automatically a leak - the roster panel renders
`display_name` and that is the panel's purpose. What it must be is ESCAPED: that
name was typed by a stranger, travels through the enka.network showcase, and
lands inside an Electron window, which makes an unescaped interpolation a stored
cross-site scripting hole with a third-party author. `surface/render.py` routes
every interpolation through `html.escape(..., quote=True)` including inside
attributes, and `tests/test_surface_render.py` pins both the element case and
the attribute break-out case. **Any NEW interpolation added to the renderer gets
the same escape and its own pin, in the same slice.**

## 7. HIERARCHY

- **The most important thing on the page is the most prominent thing on the
  page.** State what you believe the most important element is, then say whether
  the rendering agrees.
- Watch for hierarchy inverted by an INERT class: a dimming class that no rule
  actually defines leaves the "dimmed" text rendering BRIGHTER than the content
  it was meant to sit behind. Same root cause as failure class 1, and it is
  caught the same way - by computed value.
- Freshness must not be readable as currency. The dashboard renders a SNAPSHOT
  written by the headless lane, not a live query, so a stale reading that looks
  identical to a fresh one is a correctness defect wearing a styling costume.
  `surface/render.py` gives stale its own colour for exactly this reason.
- A panel that is not live says what it is waiting on and shows NO placeholder
  number. That is the invariant ADR-005 exists for, it is stated in the page
  footer, and `scripts/qa_companion.py` checks it - if the audit finds a case the
  script missed, the script is what needs extending.

## 8. Severity, and who fixes what

Three levels, and only one of them blocks:

- **MUST-FIX** - the page is wrong, unreachable, leaking, non-ASCII, or
  misrepresents state. **Fixed in the SAME slice.** No exceptions and no
  deferrals.
- **SHOULD-FIX** - real, not blocking. Logged as a `ROADMAP.md` item with the
  measurement attached, so the next session finds a finding rather than an
  opinion.
- **NICE-TO-HAVE** - taste. Say it once, log it, and move on.

Every finding names the file, the element and the MEASUREMENT - a computed
value, a rect, a ratio with its pair, a code point. **A finding with no
measurement is an opinion**, and an opinion cannot be re-checked by the next
agent.

## 9. The verdict - byte-exact, and the last line

The controller string-matches this line, so it is exactly one of these two, with
no adornment, no bold, and nothing after it:

```
AUDIT: PASS
```

```
AUDIT: BLOCKED - <n> MUST-FIX open
```

- `PASS` means every phase ran and zero MUST-FIX findings remain OPEN. It does
  not mean zero were found - a MUST-FIX found and fixed in this slice is a pass,
  and the report says so above the verdict.
- `BLOCKED` means the count is non-zero. **Do not round a BLOCKED up to a PASS
  because the remaining item is small**, and do not commit over it. Per
  `.claude/commands/orchestrated-run.md` phase 7, the merge waits on this
  verdict, and the audit is the thing that must have happened before the commit
  rather than after it.
- Above the verdict, report each phase with what you observed, every finding
  with its measurement, and anything you could NOT measure - labelled
  unmeasured, never rounded up to clean.
