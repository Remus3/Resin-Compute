"use strict";

// Grades the DEGRADED paths of shell/lib/geometry.js: work areas that are not
// rectangles, negative and positive display origins, the exact visibility
// boundary, remembered values that are not rectangles, a display smaller than
// the default window, and overlapArea's edges. The common offscreen recovery
// cases are in lib.test.js; nothing here repeats them.
//
// Every test names the geometry.js line it exercises. The module imports
// nothing, so this runs with no electron binary and no display server.

const test = require("node:test");
const assert = require("node:assert/strict");

const geometry = require("../lib/geometry.js");

const PRIMARY = Object.freeze({ x: 0, y: 0, width: 1920, height: 1040 });
const LEFT_MONITOR = Object.freeze({ x: -1920, y: 0, width: 1920, height: 1040 });
const RIGHT_MONITOR = Object.freeze({ x: 1920, y: 0, width: 1920, height: 1040 });
const DEFAULT_AT_ORIGIN = Object.freeze({
  x: 0,
  y: 0,
  width: geometry.DEFAULT_WIDTH,
  height: geometry.DEFAULT_HEIGHT,
});

test("a work area that is not a rectangle yields the default size at the origin", () => {
  // geometry.js:81 - `!isRect(workArea)`. The display toolkit normally supplies
  // this, but a headless run or a toolkit error can hand over anything, and
  // the module answers with the one rectangle that invents no screen fact.
  for (const bad of [null, undefined, [0, 0, 1920, 1040], "1920x1040", 42, { width: 1920, height: 1040 }]) {
    assert.deepEqual(geometry.place(null, bad), DEFAULT_AT_ORIGIN, JSON.stringify(bad));
    assert.deepEqual(
      geometry.place({ x: 10, y: 10, width: 700, height: 500 }, bad),
      DEFAULT_AT_ORIGIN,
      JSON.stringify(bad),
    );
  }
});

test("a work area with a negative width or height is refused like an empty one", () => {
  // geometry.js:81 - `workArea.width <= 0 || workArea.height <= 0`. isRect has
  // no sign check, so this clause is the only thing between a toolkit bug and
  // a window centred at a negative half-width.
  for (const bad of [{ ...PRIMARY, width: -1920 }, { ...PRIMARY, height: -1040 }, { ...PRIMARY, width: -1, height: -1 }]) {
    assert.deepEqual(geometry.place(null, bad), DEFAULT_AT_ORIGIN, JSON.stringify(bad));
  }
});

test("a work area with a negative origin keeps a window on that monitor", () => {
  // geometry.js:106-107 - the nudge clamps against workArea.x and workArea.y,
  // not against zero. A monitor to the left of the primary has negative
  // coordinates throughout, and clamping to zero would drag every window on it
  // onto the primary.
  const remembered = { x: -1800, y: 100, width: 700, height: 500 };
  assert.deepEqual(geometry.place(remembered, LEFT_MONITOR), remembered);
  // Past the monitor's own left edge: nudged back to that edge, not to zero.
  const past = { x: -2000, y: 100, width: 700, height: 500 };
  assert.deepEqual(geometry.place(past, LEFT_MONITOR), { x: -1920, y: 100, width: 700, height: 500 });
});

test("a work area with a positive origin centres and nudges relative to it", () => {
  // geometry.js:62-70 - centred adds workArea.x and workArea.y; :106-107 - the
  // nudge's far edge is workArea.x + workArea.width. A second monitor to the
  // right starts at x=1920, and a window placed relative to zero would land on
  // the primary instead.
  assert.deepEqual(geometry.place(null, RIGHT_MONITOR), {
    x: 1920 + Math.round((1920 - geometry.DEFAULT_WIDTH) / 2),
    y: Math.round((1040 - geometry.DEFAULT_HEIGHT) / 2),
    width: geometry.DEFAULT_WIDTH,
    height: geometry.DEFAULT_HEIGHT,
  });
  const drifted = { x: 3500, y: 700, width: 700, height: 500 };
  assert.deepEqual(geometry.place(drifted, RIGHT_MONITOR), {
    x: 1920 + 1920 - 700,
    y: 1040 - 500,
    width: 700,
    height: 500,
  });
});

test("exactly a quarter visible is nudged, not centred", () => {
  // geometry.js:98 - `visible < width * height * MIN_VISIBLE_FRACTION`, strict.
  // The boundary case decides which branch a window on the corner takes, and
  // "at least a quarter" is the documented meaning at :28-33.
  const corner = { x: 1570, y: 790, width: 700, height: 500 };
  const visible = geometry.overlapArea(corner, PRIMARY);
  assert.equal(visible, 700 * 500 * geometry.MIN_VISIBLE_FRACTION, "precondition: exactly on the boundary");
  assert.deepEqual(geometry.place(corner, PRIMARY), { x: 1920 - 700, y: 1040 - 500, width: 700, height: 500 });
  // One column of pixels less visible and it is centred instead.
  const justUnder = { x: 1571, y: 790, width: 700, height: 500 };
  assert.ok(geometry.overlapArea(justUnder, PRIMARY) < visible, "precondition: below the boundary");
  assert.deepEqual(geometry.place(justUnder, PRIMARY), geometry.centred(PRIMARY));
});

test("a remembered value that is not an integer rectangle reads as nothing remembered", () => {
  // geometry.js:89 - `!isRect(remembered)`. state.js refuses these before they
  // are ever remembered, but the two modules must agree independently: a float
  // from a toolkit's bounds on a scaled display must centre, not propagate.
  for (const bad of [
    undefined,
    "700x500",
    42,
    [10, 10, 700, 500],
    { x: 10.5, y: 10, width: 700, height: 500 },
    { x: 10, y: 10, width: 700 },
  ]) {
    assert.deepEqual(geometry.place(bad, PRIMARY), geometry.centred(PRIMARY), JSON.stringify(bad));
  }
});

test("a work area smaller than the default shrinks the centred window to fit", () => {
  // geometry.js:63-64 - Math.min against the work area on both axes. A small
  // laptop panel must get a window it can show whole, not one hanging off two
  // edges by the default's excess.
  const small = { x: 0, y: 0, width: 800, height: 600 };
  assert.ok(small.width < geometry.DEFAULT_WIDTH && small.height < geometry.DEFAULT_HEIGHT, "precondition");
  assert.deepEqual(geometry.place(null, small), { x: 0, y: 0, width: 800, height: 600 });
});

test("centred always yields integer coordinates", () => {
  // geometry.js:66-67 - Math.round. A toolkit given a half-pixel position
  // rounds it somewhere the caller cannot see, and a remembered-then-restored
  // window would drift by a pixel per launch.
  const odd = { x: 0, y: 0, width: 1921, height: 1041 };
  const rect = geometry.centred(odd);
  for (const key of ["x", "y", "width", "height"]) {
    assert.ok(Number.isInteger(rect[key]), `${key}=${rect[key]}`);
  }
});

test("overlapArea: touching edges are zero, containment is the inner area, partial is exact, symmetric", () => {
  // geometry.js:48-59 - the arithmetic cases behind the one disjoint check in
  // lib.test.js. `width <= 0 || height <= 0` at :55 is why touching is zero.
  const a = { x: 0, y: 0, width: 10, height: 10 };
  assert.equal(geometry.overlapArea(a, { x: 10, y: 0, width: 10, height: 10 }), 0, "touching on the right");
  assert.equal(geometry.overlapArea(a, { x: 0, y: 10, width: 10, height: 10 }), 0, "touching below");
  const outer = { x: 0, y: 0, width: 100, height: 100 };
  const inner = { x: 10, y: 10, width: 20, height: 20 };
  assert.equal(geometry.overlapArea(outer, inner), 400, "containment");
  const b = { x: 5, y: 5, width: 10, height: 10 };
  assert.equal(geometry.overlapArea(a, b), 25, "partial");
  for (const [p, q] of [[a, b], [outer, inner], [a, outer]]) {
    assert.equal(geometry.overlapArea(p, q), geometry.overlapArea(q, p), "symmetric");
  }
  assert.equal(geometry.overlapArea(a, a), 100, "self");
});

test("isRect refuses null, arrays, floats, NaN, strings and missing keys directly", () => {
  // geometry.js:35-45 - every clause of the conjunction. Reached only through
  // place in lib.test.js, so a clause dropped there would have shown up as a
  // wrong placement, not as a wrong predicate. A negative POSITION is a valid
  // rectangle: the left monitor is nothing but negative positions.
  assert.equal(geometry.isRect({ x: 0, y: 0, width: 1, height: 1 }), true);
  assert.equal(geometry.isRect({ x: -5, y: -5, width: 1, height: 1 }), true, "a negative position is a position");
  for (const bad of [
    null,
    undefined,
    [0, 0, 1, 1],
    "rect",
    42,
    { x: 0, y: 0, width: 1 },
    { x: 0.5, y: 0, width: 1, height: 1 },
    { x: 0, y: 0, width: NaN, height: 1 },
    { x: 0, y: 0, width: 1, height: Infinity },
    { x: "0", y: 0, width: 1, height: 1 },
  ]) {
    assert.equal(geometry.isRect(bad), false, JSON.stringify(bad));
  }
});
