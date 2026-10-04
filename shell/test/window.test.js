"use strict";

// Grades the DEGRADED paths of shell/lib/window.js: no bounds at all, flags
// given as strings or numbers, the preload path, the two security flags
// lib.test.js does not name, object freshness, and alwaysOnTop's non-boolean
// and non-string inputs. The four security flags, the hidden start and the
// precedence rule are in lib.test.js; nothing here repeats them.
//
// Every test names the window.js line it exercises. The module imports
// nothing; this file imports node:fs and node:path for one existence check
// and never electron.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const windowLib = require("../lib/window.js");
const geometry = require("../lib/geometry.js");

test("options with no bounds leaves the rectangle undefined rather than inventing one", () => {
  // window.js:72-79 - `input.bounds ?? {}` and four reads off it. The module
  // builds options from what it is given; geometry.place is the one place a
  // rectangle is decided, and a default here would be a second answer.
  for (const args of [undefined, null, {}, { bounds: null }, { bounds: undefined }]) {
    const opts = windowLib.options(args);
    for (const key of ["x", "y", "width", "height"]) {
      assert.equal(opts[key], undefined, `${JSON.stringify(args)} ${key}`);
    }
    assert.equal(opts.minWidth, geometry.MIN_WIDTH);
    assert.equal(opts.minHeight, geometry.MIN_HEIGHT);
  }
});

test("the window minimums agree with the geometry minimums", () => {
  // window.js:80-81 carry the two minimums as literals; geometry.js:24-25 own
  // them. Two copies across two files, and this is the only thing that notices
  // when one moves without the other.
  const opts = windowLib.options({ bounds: { x: 0, y: 0, width: 900, height: 620 } });
  assert.equal(opts.minWidth, geometry.MIN_WIDTH);
  assert.equal(opts.minHeight, geometry.MIN_HEIGHT);
});

test("alwaysOnTop and show are set by value, so the string true is false", () => {
  // window.js:94 and :98 - `=== true`. The rule state.js applies to the file
  // applies to the options: a truthy non-boolean is a mistake upstream, and
  // coercing it would hide the mistake behind a window that happens to behave.
  for (const truthy of ["true", 1, "yes", {}, [], "1"]) {
    const opts = windowLib.options({ alwaysOnTop: truthy, show: truthy });
    assert.equal(opts.alwaysOnTop, false, JSON.stringify(truthy));
    assert.equal(opts.show, false, JSON.stringify(truthy));
  }
  const opts = windowLib.options({ alwaysOnTop: true, show: true });
  assert.equal(opts.alwaysOnTop, true);
  assert.equal(opts.show, true);
});

test("the preload path is carried into webPreferences untouched", () => {
  // window.js:101 - `preload: input.preloadPath`. main.js:267 computes the path
  // from its own __dirname; any normalisation here would be a second opinion
  // about where the file is.
  const preloadPath = path.join("some where", "with spaces", windowLib.PRELOAD_FILENAME);
  assert.equal(windowLib.options({ preloadPath }).webPreferences.preload, preloadPath);
  assert.equal(windowLib.options({}).webPreferences.preload, undefined);
});

test("experimental features and insecure content stay off, and no undeclared preference appears", () => {
  // window.js:106-107 - the two flags lib.test.js does not name by value. Both
  // are wrong by omission like the four it does, so both are pinned by value,
  // and the key set is pinned so a new preference has to be declared here.
  const prefs = windowLib.options({}).webPreferences;
  assert.equal(prefs.experimentalFeatures, false);
  assert.equal(prefs.allowRunningInsecureContent, false);
  assert.deepEqual(Object.keys(prefs).sort(), [
    "allowRunningInsecureContent",
    "contextIsolation",
    "experimentalFeatures",
    "nodeIntegration",
    "preload",
    "sandbox",
    "webSecurity",
  ]);
});

test("the frame, menu bar and colour choices are the documented ones", () => {
  // window.js:86-92 - opaque, dark background, no menu bar. The background is
  // #rrggbb so the toolkit paints the page's dark before the page has painted
  // anything; lib.test.js pins frame and skipTaskbar.
  const opts = windowLib.options({});
  assert.equal(opts.transparent, false);
  assert.equal(opts.autoHideMenuBar, true);
  assert.match(opts.backgroundColor, /^#[0-9a-f]{6}$/);
});

test("options returns a fresh object every call", () => {
  // window.js:75 - an object literal per call, nested webPreferences included.
  // main.js hands the result to the toolkit, which may keep it; a shared
  // object would let one window's edits leak into the next.
  const first = windowLib.options({});
  const second = windowLib.options({});
  assert.notEqual(first, second);
  assert.notEqual(first.webPreferences, second.webPreferences);
  first.webPreferences.sandbox = false;
  assert.equal(windowLib.options({}).webPreferences.sandbox, true);
});

test("alwaysOnTop of a non-object is false", () => {
  // window.js:44 - `sources && typeof sources === "object" ? sources : {}`.
  for (const bad of [null, undefined, "true", 1, true]) {
    assert.equal(windowLib.alwaysOnTop(bad), false, String(bad));
  }
});

test("alwaysOnTop ignores a non-boolean flag and falls through", () => {
  // window.js:45 - `typeof input.flag === "boolean"`. A flag parsed from argv
  // is a string until somebody converts it, and the string "false" must not
  // pin the window.
  assert.equal(windowLib.alwaysOnTop({ flag: "false", env: "1" }), true, "string flag skipped, env read");
  assert.equal(windowLib.alwaysOnTop({ flag: "true" }), false, "string flag skipped, nothing else");
  assert.equal(windowLib.alwaysOnTop({ flag: 1, remembered: false }), false, "numeric flag skipped");
  assert.equal(windowLib.alwaysOnTop({ flag: 0, remembered: true }), true, "numeric flag skipped, remembered read");
});

test("alwaysOnTop ignores a non-string or blank environment value", () => {
  // window.js:50 - `typeof input.env === "string" && input.env.trim() !== ""`.
  // process.env only carries strings, but the parameter is any object, and a
  // blank variable means unset.
  assert.equal(windowLib.alwaysOnTop({ env: 1, remembered: true }), true, "numeric env skipped");
  assert.equal(windowLib.alwaysOnTop({ env: true, remembered: false }), false, "boolean env skipped");
  assert.equal(windowLib.alwaysOnTop({ env: "   ", remembered: true }), true, "blank env skipped");
  assert.equal(windowLib.alwaysOnTop({ env: "", remembered: true }), true, "empty env skipped");
});

test("alwaysOnTop ignores a non-boolean remembered value", () => {
  // window.js:59 - `typeof input.remembered === "boolean"`. state.js already
  // refuses a string here, but the two modules must agree independently.
  for (const bad of ["true", 1, "yes", {}]) {
    assert.equal(windowLib.alwaysOnTop({ remembered: bad }), false, JSON.stringify(bad));
  }
});

test("PRELOAD_FILENAME names a file that ships beside the libs", () => {
  // window.js:29 - a bare filename relative to shell/. main.js:267 joins it
  // with its own directory; if the file moved, the renderer would start with
  // no bridge and nothing would say so until the page tried to use one.
  const preload = path.join(__dirname, "..", windowLib.PRELOAD_FILENAME);
  assert.ok(fs.existsSync(preload), preload);
  assert.equal(path.basename(windowLib.PRELOAD_FILENAME), windowLib.PRELOAD_FILENAME, "a bare filename, not a path");
});
