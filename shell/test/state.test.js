"use strict";

// Grades the DEGRADED paths of shell/lib/state.js: a hostile key in the file,
// fields of the wrong type inside bounds, serialising nothing, serialising a
// string, NaN on the way out, and the shape of the text written. The totality
// of parse and the "false" string are in lib.test.js; nothing here repeats them.
//
// Every test names the state.js line it exercises. The module imports nothing,
// so this runs with no electron binary and no filesystem.

const test = require("node:test");
const assert = require("node:assert/strict");

const state = require("../lib/state.js");

const GOOD_BOUNDS = Object.freeze({ x: 10, y: 20, width: 800, height: 600 });

test("a prototype key in the file reaches neither the state nor the prototype", () => {
  // state.js:72 - JSON.parse makes "__proto__" an OWN property, and :82-85 read
  // only the two declared fields by name. An operator-editable file is an
  // attack surface for exactly one reader, and this is it.
  const before = Object.prototype.alwaysOnTop;
  const parsed = state.parse('{"__proto__":{"alwaysOnTop":true,"bounds":{"x":1,"y":2,"width":3,"height":4}}}');
  assert.deepEqual(parsed, { alwaysOnTop: false, bounds: null });
  assert.equal(Object.prototype.alwaysOnTop, before);
  assert.equal(Object.hasOwn(parsed, "__proto__"), false);
});

test("parse returns a fresh object and never the frozen defaults themselves", () => {
  // state.js:67, :74, :78 - `{ ...DEFAULTS }`, three times. main.js:73 holds
  // stateLib.DEFAULTS directly as its initial value, so a parse that handed
  // back the same frozen object would give every caller a value it cannot
  // update in place, and the first in-place write would throw under strict.
  assert.ok(Object.isFrozen(state.DEFAULTS), "DEFAULTS is frozen");
  for (const bad of [null, "", "{not json", "[]"]) {
    const parsed = state.parse(bad);
    assert.notEqual(parsed, state.DEFAULTS, String(bad));
    parsed.alwaysOnTop = true;
    assert.equal(state.DEFAULTS.alwaysOnTop, false, String(bad));
  }
});

test("a bounds field of the wrong type drops the whole bounds, not just the field", () => {
  // state.js:51 - Number.isInteger on every key, inside isBounds, and :85
  // falls to DEFAULTS.bounds on a false. A half-valid rectangle is not a
  // rectangle the window toolkit can place.
  for (const field of ['"10"', "true", "null", "[10]", "{}"]) {
    const text = `{"bounds":{"x":${field},"y":20,"width":800,"height":600}}`;
    assert.equal(state.parse(text).bounds, null, text);
  }
});

test("isBounds refuses everything that is not exactly four integer keys", () => {
  // state.js:43-52 - the direct arms. lib.test.js reaches isBounds through
  // parse for the key-count cases and directly for NaN and Infinity only.
  assert.equal(state.isBounds(GOOD_BOUNDS), true);
  for (const bad of [
    null,
    undefined,
    "x",
    42,
    [10, 20, 800, 600],
    { x: 10, y: 20, width: 800 },
    { x: 10, y: 20, width: 800, height: 600, extra: 0 },
    { x: 10, y: 20, width: 800, depth: 600 },
    { x: "10", y: 20, width: 800, height: 600 },
    { x: 10.5, y: 20, width: 800, height: 600 },
  ]) {
    assert.equal(state.isBounds(bad), false, JSON.stringify(bad));
  }
});

test("serialising nothing writes the defaults document", () => {
  // state.js:100 - `state ?? {}`. The first save of a fresh install happens
  // before anything was ever read; it must write a valid file, not "null".
  const expected = `${JSON.stringify(state.DEFAULTS, null, 2)}\n`;
  assert.equal(state.serialize(undefined), expected);
  assert.equal(state.serialize(null), expected);
  assert.equal(state.serialize({}), expected);
});

test("serialising accepts a JSON string as well as an object", () => {
  // state.js:100 - the string branch of the ternary. Text read from the file
  // can be normalised and written back without an intermediate parse call at
  // the caller, which is one fewer place to forget the validation.
  const text = state.serialize('{"alwaysOnTop":true,"bounds":null,"junk":1}');
  assert.deepEqual(JSON.parse(text), { alwaysOnTop: true, bounds: null });
  assert.deepEqual(JSON.parse(state.serialize("{not json")), { ...state.DEFAULTS });
});

test("NaN bounds serialise as no bounds, never as the token NaN", () => {
  // state.js:100-101 - JSON.stringify writes NaN as null, and the parse on the
  // way back then refuses the rectangle at :51. The file never carries a value
  // JSON cannot represent, and the next launch centres rather than crashing.
  const text = state.serialize({ alwaysOnTop: false, bounds: { x: NaN, y: 0, width: 10, height: 10 } });
  assert.ok(!text.includes("NaN"));
  assert.equal(JSON.parse(text).bounds, null);
});

test("parse of serialize is the identity on valid state", () => {
  // state.js:65 and :99 - the two halves of the file format. If they drift, a
  // remembered position survives exactly one launch.
  for (const valid of [
    { alwaysOnTop: false, bounds: null },
    { alwaysOnTop: true, bounds: null },
    { alwaysOnTop: true, bounds: { ...GOOD_BOUNDS } },
    { alwaysOnTop: false, bounds: { x: -1800, y: 0, width: 360, height: 320 } },
  ]) {
    assert.deepEqual(state.parse(state.serialize(valid)), valid);
  }
});

test("the serialised text is 7-bit ASCII, two-space indented, one trailing newline", () => {
  // state.js:101 - JSON.stringify(safe, null, 2) plus "\n". The file is one an
  // operator may open in a text editor, so it is laid out for a person, and it
  // is ASCII because the glyph gate sweeps this tree and nothing it writes
  // should be the thing that trips it.
  const text = state.serialize({ alwaysOnTop: true, bounds: { ...GOOD_BOUNDS } });
  for (const char of text) {
    assert.ok(char.charCodeAt(0) < 0x80, `non-ASCII: U+${char.charCodeAt(0).toString(16)}`);
  }
  assert.ok(text.endsWith("}\n"), JSON.stringify(text));
  assert.ok(!text.endsWith("\n\n"), JSON.stringify(text));
  assert.ok(!text.includes("\r"), JSON.stringify(text));
  const lines = text.split("\n");
  assert.equal(lines[0], "{");
  assert.ok(lines[1].startsWith('  "'), lines[1]);
});

test("BOUNDS_KEYS is exactly x y width height and cannot be grown at runtime", () => {
  // state.js:35 - Object.freeze([...]). isBounds at :48 compares key COUNT to
  // this list's length, so a key pushed onto it would silently loosen the
  // rectangle check for every later parse.
  assert.deepEqual([...state.BOUNDS_KEYS], ["x", "y", "width", "height"]);
  assert.ok(Object.isFrozen(state.BOUNDS_KEYS));
  assert.throws(() => state.BOUNDS_KEYS.push("depth"), TypeError);
});
