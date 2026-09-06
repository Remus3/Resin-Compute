"use strict";

// WHERE THE WINDOW OPENS. Pure arithmetic over rectangles.
//
// THE PROBLEM THIS SOLVES IS NOT HYPOTHETICAL. Remembered bounds are restored on
// the next launch, and between the two launches a display can be unplugged, its
// resolution changed, or a laptop undocked. A window restored to coordinates on
// a monitor that is no longer there opens OFFSCREEN: it exists, it has focus, it
// responds to the tray, and it is invisible. The operator's only recovery is to
// find and delete a preferences file they were never told about.
//
// So a remembered rectangle is CLAMPED into the work area rather than trusted,
// and a rectangle with no useful overlap is discarded for the default instead.
//
// PURE, and it takes the work area as an argument rather than asking a display
// toolkit for it. That is what makes the undocked-monitor case a two-line test
// instead of an unreproducible bug report.

/** Default window size. Wide enough for three dashboard cards on one row. */
const DEFAULT_WIDTH = 900;
const DEFAULT_HEIGHT = 620;

/** Below this the dashboard grid collapses to one column and stops being glanceable. */
const MIN_WIDTH = 360;
const MIN_HEIGHT = 320;

/**
 * How much of a restored window must land on screen to be considered usable.
 *
 * A window peeking one pixel onto the display is technically visible and
 * practically lost, so a fraction rather than a nonzero test.
 */
const MIN_VISIBLE_FRACTION = 0.25;

function isRect(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Number.isInteger(value.x) &&
    Number.isInteger(value.y) &&
    Number.isInteger(value.width) &&
    Number.isInteger(value.height)
  );
}

/** Area of the intersection of two rectangles. Zero when they do not overlap. */
function overlapArea(a, b) {
  const left = Math.max(a.x, b.x);
  const top = Math.max(a.y, b.y);
  const right = Math.min(a.x + a.width, b.x + b.width);
  const bottom = Math.min(a.y + a.height, b.y + b.height);
  const width = right - left;
  const height = bottom - top;
  if (width <= 0 || height <= 0) {
    return 0;
  }
  return width * height;
}

/** The default rectangle, centred in a work area. */
function centred(workArea) {
  const width = Math.min(DEFAULT_WIDTH, workArea.width);
  const height = Math.min(DEFAULT_HEIGHT, workArea.height);
  return {
    x: workArea.x + Math.round((workArea.width - width) / 2),
    y: workArea.y + Math.round((workArea.height - height) / 2),
    width,
    height,
  };
}

/**
 * Decide the window rectangle for this launch.
 *
 * @param {object|null} remembered Bounds from the previous run, or null.
 * @param {object} workArea The display's usable area, taskbar excluded.
 * @returns {{x:number,y:number,width:number,height:number}}
 */
function place(remembered, workArea) {
  if (!isRect(workArea) || workArea.width <= 0 || workArea.height <= 0) {
    // Nothing sensible can be computed against a nonsense work area, and
    // guessing a screen size would be inventing a fact. The default SIZE at the
    // origin is the honest answer: it is at worst wrong in the same way the
    // caller's input was.
    return { x: 0, y: 0, width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT };
  }

  if (!isRect(remembered)) {
    return centred(workArea);
  }

  const width = Math.max(MIN_WIDTH, Math.min(remembered.width, workArea.width));
  const height = Math.max(MIN_HEIGHT, Math.min(remembered.height, workArea.height));

  const candidate = { x: remembered.x, y: remembered.y, width, height };
  const visible = overlapArea(candidate, workArea);
  if (visible < width * height * MIN_VISIBLE_FRACTION) {
    // The display it was on is gone, or moved. Centre rather than clamp: a
    // clamped window slams against whichever edge it drifted past, which looks
    // like a bug even though it is recoverable.
    return centred(workArea);
  }

  // Enough of it is on screen. Nudge the rest on.
  const x = Math.max(workArea.x, Math.min(candidate.x, workArea.x + workArea.width - width));
  const y = Math.max(workArea.y, Math.min(candidate.y, workArea.y + workArea.height - height));
  return { x, y, width, height };
}

module.exports = {
  DEFAULT_HEIGHT,
  DEFAULT_WIDTH,
  MIN_HEIGHT,
  MIN_VISIBLE_FRACTION,
  MIN_WIDTH,
  centred,
  isRect,
  overlapArea,
  place,
};
