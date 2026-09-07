# ADR-005: An Electron companion window over a local dashboard surface

**Status:** Accepted
**Date:** 2026-09-06
**Relates to:** ADR-001, which rejected a TypeScript frontend as premature

## Context

ADR-001 chose Python over TypeScript so that the inheritance from the parent
project was real rather than nominal, and it rejected a frontend on the grounds
that there was no specified UI. ROADMAP carried that forward under "Later":

> **Dashboard.** Explicitly out of scope for the scaffold. ADR-001 rejected a
> TypeScript frontend as premature. Revisit when there is a specified UI, and
> give it its own ADR rather than reopening ADR-001.

The operator has now specified one, and the reason is not cosmetic. The stated
requirement is that the dashboard exists **before** further feature work, so that
each feature becomes visible as it lands rather than after it lands. A headless
lane with no surface has a real failure mode: work accumulates that nobody has
looked at, and a planner that decomposes goals into an empty cost table looks
identical, from the outside, to one that decomposes them correctly.

## Decision

Build an **Electron companion window** that loads a **local HTTP dashboard
surface**, on the Sibling-A model - the sibling project that already solved
this, an Electron shell over a local HTTP dashboard whose patterns are proven
on this machine.

Three parts, and the split is the decision:

1. **`surface/`** - a stdlib-only Python HTTP server on 8791 that renders the
   dashboard. It is the whole of the UI. It runs in an ordinary browser with no
   Electron present, which is what keeps it gradable in the normal test suite.
2. **`shell/`** - an Electron main process that opens a frameless window onto
   that surface, plus a system tray so closing the window hides it rather than
   quitting.
3. **`scripts/make_shortcut.py`** - an idempotent desktop shortcut.

**ADR-001 is NOT reopened.** Its subject was the language of the compute tree,
and that answer is unchanged: every calculation stays in Python, and the surface
is Python too. Node exists in this repository solely to host a window. The
runtime dependency list for everything under `core/`, `engines/`, `ingest/`,
`headless/` and `surface/` remains empty.

## The rule the shell is built under, inherited from Sibling-A

**`shell/main.js` is wiring only.** It imports Electron, so nothing can load it
in a test, so nothing that makes a decision may live there. What the window IS,
where it opens, what the tray shows and what is remembered between launches all
live in `shell/lib/*.js` as pure modules with no Electron import, each graded by
`shell/test/*.test.js` under `node --test` on a machine with no display server.

Sibling-A records exactly what happens when that rule is broken: its certificate
verdict map lived in `main.js`, nothing could load the file, so no test graded the
argument handed to the verification callback, and changing it to a blanket accept
left the whole gate green. The rule is not style.

## Panels declare their own readiness, and never fake a number

The operator's reason for wanting this now is to watch features arrive. That only
works if a panel with no data behind it says so.

Every panel therefore reports one of three states - **ready**, **partial** or
**not wired** - and a panel that is not ready renders what it is waiting on
instead of a plausible zero. This is the same distinction `engines/objectives.py`
already draws between a cost of zero and a cost that is unknown, applied to the
UI: a dashboard that renders "0 resin required" for a plan built on an empty cost
table is not a neutral placeholder, it is a wrong answer displayed confidently.

## Consequences

- Node and Electron enter the tree, pinned, under `shell/` only. CI must not be
  made to depend on the Electron binary: the package declares no postinstall and
  fetches its platform binary lazily on first `require`, so a checkout that has
  run only `npm install` has no `electron.exe`. Everything gradable is gradable
  without it.
- `surface/` is stdlib-only and is covered by the ordinary `tests` suite.
- The surface binds 8791 from the block reserved in ADR-004, on loopback.
- Unlike Sibling-A, this surface is **plain HTTP, not HTTPS with a pinned
  certificate.** Sibling-A's dashboard carries data worth pinning a certificate
  over; this one renders a Genshin roster and a resin count on loopback. If it
  ever leaves loopback that decision is revisited, and it gets its own ADR.

## Rejected

- **A web app with no shell.** The operator asked for an overlay and a tray, and
  a browser tab is neither. It also cannot stay above a fullscreen game.
- **A Python GUI toolkit.** It would keep the tree single-language, but no
  sibling on this machine uses one, so there is no proven pattern to inherit, and
  the parent project's own companion is Electron.
- **Putting the UI inside PityEngine's HTTP service.** The engine is pure,
  deterministic and versioned, holds no account state and reads no file. Serving
  a stateful dashboard from it would destroy the property that makes it testable.
