"use strict";

// Grades endpoint, state, geometry, window and supervisor. All five import
// nothing, so this runs with no electron binary and no display server.

const test = require("node:test");
const assert = require("node:assert/strict");

const endpoint = require("../lib/endpoint.js");
const state = require("../lib/state.js");
const geometry = require("../lib/geometry.js");
const windowLib = require("../lib/window.js");
const supervisor = require("../lib/supervisor.js");

// ---------------------------------------------------------------------------
// endpoint
// ---------------------------------------------------------------------------

test("endpoint defaults to loopback on the port ADR-004 assigned", () => {
  const resolved = endpoint.resolve({});
  assert.equal(resolved.host, "127.0.0.1");
  assert.equal(resolved.port, 8791);
  assert.equal(resolved.url, "http://127.0.0.1:8791/");
});

test("endpoint reads the environment it is given, not the real one", () => {
  const resolved = endpoint.resolve({ RESIN_DASHBOARD_PORT: "8795" });
  assert.equal(resolved.port, 8795);
});

test("endpoint refuses a non-loopback host", () => {
  // ADR-005 rests the whole no-authentication decision on never leaving the box,
  // so this is a control rather than a preference. A warning would not be one.
  for (const host of ["0.0.0.0", "example.com", "192.168.1.5"]) {
    assert.throws(() => endpoint.resolve({ RESIN_DASHBOARD_HOST: host }), endpoint.EndpointError);
  }
});

test("endpoint accepts every spelling of loopback", () => {
  for (const host of ["127.0.0.1", "localhost", "::1", "[::1]"]) {
    assert.ok(endpoint.isLoopback(host), host);
  }
});

test("endpoint refuses a port that is not plain digits", () => {
  // Number() would accept all of these. None is a port an operator meant to type.
  for (const port of ["0x10", "1e3", " 12 x", "-1", "80.5", "abc"]) {
    assert.throws(() => endpoint.resolve({ RESIN_DASHBOARD_PORT: port }), endpoint.EndpointError);
  }
});

test("endpoint refuses a port outside the valid range", () => {
  for (const port of ["0", "65536", "99999"]) {
    assert.throws(() => endpoint.resolve({ RESIN_DASHBOARD_PORT: port }), endpoint.EndpointError);
  }
});

test("an endpoint refusal never interpolates the offending value", () => {
  try {
    endpoint.resolve({ RESIN_DASHBOARD_HOST: "SENTINEL.example.com" });
    assert.fail("expected a refusal");
  } catch (error) {
    assert.ok(!error.message.includes("SENTINEL"));
  }
});

// ---------------------------------------------------------------------------
// state
// ---------------------------------------------------------------------------

test("state parsing is total - every malformed input yields the defaults", () => {
  for (const bad of [null, undefined, "", "   ", "{not json", "[]", "42", '"text"', "null"]) {
    const parsed = state.parse(bad);
    assert.equal(parsed.alwaysOnTop, false);
    assert.equal(parsed.bounds, null);
  }
});

test("the string false does not become true", () => {
  // The defect this module exists to prevent. Boolean("false") is true.
  assert.equal(state.parse('{"alwaysOnTop":"false"}').alwaysOnTop, false);
  assert.equal(state.parse('{"alwaysOnTop":"true"}').alwaysOnTop, false);
  assert.equal(state.parse('{"alwaysOnTop":1}').alwaysOnTop, false);
  assert.equal(state.parse('{"alwaysOnTop":true}').alwaysOnTop, true);
  assert.equal(state.parse('{"alwaysOnTop":false}').alwaysOnTop, false);
});

test("bounds survive a round trip only when all four fields are integers", () => {
  const good = '{"bounds":{"x":10,"y":20,"width":800,"height":600}}';
  assert.deepEqual(state.parse(good).bounds, { x: 10, y: 20, width: 800, height: 600 });

  for (const bad of [
    '{"bounds":{"x":10,"y":20,"width":800}}',
    '{"bounds":{"x":10,"y":20,"width":800,"height":600,"extra":1}}',
    '{"bounds":{"x":1.5,"y":20,"width":800,"height":600}}',
    '{"bounds":[10,20,800,600]}',
    '{"bounds":null}',
  ]) {
    assert.equal(state.parse(bad).bounds, null, bad);
  }
});

test("NaN and Infinity are refused as bounds", () => {
  assert.ok(!state.isBounds({ x: NaN, y: 0, width: 10, height: 10 }));
  assert.ok(!state.isBounds({ x: Infinity, y: 0, width: 10, height: 10 }));
});

test("serialising drops keys this module does not declare", () => {
  const text = state.serialize({ alwaysOnTop: true, bounds: null, injected: "keep me out" });
  assert.ok(!text.includes("injected"));
  assert.ok(text.endsWith("\n"));
  assert.deepEqual(Object.keys(JSON.parse(text)).sort(), ["alwaysOnTop", "bounds"]);
});

// ---------------------------------------------------------------------------
// geometry
// ---------------------------------------------------------------------------

const WORK_AREA = { x: 0, y: 0, width: 1920, height: 1040 };

test("with nothing remembered the window is centred", () => {
  const rect = geometry.place(null, WORK_AREA);
  assert.equal(rect.width, geometry.DEFAULT_WIDTH);
  assert.equal(rect.height, geometry.DEFAULT_HEIGHT);
  assert.equal(rect.x, Math.round((1920 - geometry.DEFAULT_WIDTH) / 2));
});

test("remembered bounds that are still on screen are honoured", () => {
  const remembered = { x: 100, y: 80, width: 700, height: 500 };
  assert.deepEqual(geometry.place(remembered, WORK_AREA), remembered);
});

test("bounds on a monitor that is gone are recovered, not restored offscreen", () => {
  // THE defect this module exists for. A window restored to a display that was
  // unplugged has focus, responds to the tray, and is invisible.
  const offscreen = { x: 3000, y: 1800, width: 700, height: 500 };
  const rect = geometry.place(offscreen, WORK_AREA);
  assert.ok(rect.x >= WORK_AREA.x);
  assert.ok(rect.y >= WORK_AREA.y);
  assert.ok(rect.x + rect.width <= WORK_AREA.x + WORK_AREA.width);
  assert.ok(rect.y + rect.height <= WORK_AREA.y + WORK_AREA.height);
});

test("a window mostly offscreen is centred rather than slammed against an edge", () => {
  const barely = { x: 1900, y: 1030, width: 700, height: 500 };
  const rect = geometry.place(barely, WORK_AREA);
  assert.deepEqual(rect, geometry.centred({ ...WORK_AREA, width: 1920, height: 1040 }));
});

test("a window slightly past the edge is nudged back on", () => {
  // 1400,700 leaves 520x340 of a 700x500 window on screen - 50.5%, comfortably
  // over the 25% floor - so this takes the nudge branch rather than the recover
  // branch. Written first as 1500,900, which leaves only 16.8% visible and is
  // therefore CENTRED by the rule above; the test was wrong, not the placement.
  const nudge = { x: 1400, y: 700, width: 700, height: 500 };
  const visible = geometry.overlapArea(nudge, WORK_AREA);
  assert.ok(visible > 700 * 500 * geometry.MIN_VISIBLE_FRACTION, "precondition: this is the nudge branch");

  const rect = geometry.place(nudge, WORK_AREA);
  assert.equal(rect.x + rect.width, 1920);
  assert.equal(rect.y + rect.height, 1040);
  assert.equal(rect.width, 700);
  assert.equal(rect.height, 500);
});

test("a remembered size larger than the display is clamped to it", () => {
  const huge = { x: 0, y: 0, width: 5000, height: 5000 };
  const rect = geometry.place(huge, WORK_AREA);
  assert.equal(rect.width, 1920);
  assert.equal(rect.height, 1040);
});

test("a remembered size below the minimum is raised to it", () => {
  const tiny = { x: 10, y: 10, width: 40, height: 30 };
  const rect = geometry.place(tiny, WORK_AREA);
  assert.equal(rect.width, geometry.MIN_WIDTH);
  assert.equal(rect.height, geometry.MIN_HEIGHT);
});

test("a nonsense work area yields the default size rather than a guess", () => {
  const rect = geometry.place({ x: 0, y: 0, width: 700, height: 500 }, { x: 0, y: 0, width: 0, height: 0 });
  assert.deepEqual(rect, { x: 0, y: 0, width: geometry.DEFAULT_WIDTH, height: geometry.DEFAULT_HEIGHT });
});

test("overlapArea is zero for disjoint rectangles", () => {
  assert.equal(geometry.overlapArea({ x: 0, y: 0, width: 10, height: 10 }, { x: 50, y: 50, width: 10, height: 10 }), 0);
});

// ---------------------------------------------------------------------------
// window
// ---------------------------------------------------------------------------

test("the four security flags are set by value, not by truthiness", () => {
  const prefs = windowLib.options({ bounds: { x: 0, y: 0, width: 900, height: 620 } }).webPreferences;
  assert.equal(prefs.nodeIntegration, false);
  assert.equal(prefs.contextIsolation, true);
  assert.equal(prefs.sandbox, true);
  assert.equal(prefs.webSecurity, true);
  assert.equal(prefs.allowRunningInsecureContent, false);
});

test("the window starts hidden so no white rectangle is ever shown", () => {
  assert.equal(windowLib.options({}).show, false);
  assert.equal(windowLib.options({ show: true }).show, true);
});

test("the window is frameless and off the taskbar", () => {
  const opts = windowLib.options({});
  assert.equal(opts.frame, false);
  assert.equal(opts.skipTaskbar, true);
});

test("always-on-top precedence is flag, then environment, then remembered", () => {
  assert.equal(windowLib.alwaysOnTop({ flag: true, env: "0", remembered: false }), true);
  assert.equal(windowLib.alwaysOnTop({ flag: false, env: "1", remembered: true }), false);
  assert.equal(windowLib.alwaysOnTop({ env: "1", remembered: false }), true);
  assert.equal(windowLib.alwaysOnTop({ env: "0", remembered: true }), false);
  assert.equal(windowLib.alwaysOnTop({ remembered: true }), true);
  assert.equal(windowLib.alwaysOnTop({}), false);
});

test("the environment strings 0 and false are read as false, not as truthy", () => {
  for (const raw of ["0", "false", "FALSE", "no", " false "]) {
    assert.equal(windowLib.alwaysOnTop({ env: raw }), false, raw);
  }
  for (const raw of ["1", "true", "TRUE", "yes"]) {
    assert.equal(windowLib.alwaysOnTop({ env: raw }), true, raw);
  }
});

test("an unrecognised environment value falls through to the remembered value", () => {
  assert.equal(windowLib.alwaysOnTop({ env: "maybe", remembered: true }), true);
});

test("the float level clears a fullscreen game", () => {
  // "floating" sits below a fullscreen window, which is exactly when a companion
  // for a running game is wanted.
  assert.equal(windowLib.ALWAYS_ON_TOP_LEVEL, "screen-saver");
});

// ---------------------------------------------------------------------------
// supervisor
// ---------------------------------------------------------------------------

test("the spawn argv is a list and never a command string", () => {
  const argv = supervisor.spawnArgv({ python: "python.exe", host: "127.0.0.1", port: 8791 });
  assert.ok(Array.isArray(argv));
  assert.deepEqual(argv, ["python.exe", "-m", "surface", "--host", "127.0.0.1", "--port", "8791"]);
});

test("the spawn argv defaults to the windowless interpreter", () => {
  assert.equal(supervisor.spawnArgv({})[0], "pythonw.exe");
});

test("no argv element carries a shell metacharacter", () => {
  // A list argv with shell:false is immune to quoting, but an element that
  // needed quoting is a sign somebody built a string somewhere upstream.
  for (const part of supervisor.spawnArgv({ python: "pythonw.exe", host: "127.0.0.1", port: 8791 })) {
    assert.doesNotMatch(part, /[&|;<>^"'`$]/, part);
  }
});

test("a known exit code renders a reason the operator can act on", () => {
  assert.match(supervisor.neverAnswered(2), /already held by something else/);
});

test("an unknown exit code renders the generic refusal, not a bare number", () => {
  const message = supervisor.neverAnswered(99);
  assert.equal(message, supervisor.NEVER_ANSWERED);
  assert.ok(!message.includes("99"));
});

test("no refusal names a path", () => {
  // A path under the user profile carries the Windows account name.
  for (const message of [supervisor.NOT_SPAWNED, supervisor.NEVER_ANSWERED, supervisor.NOT_LOADED, supervisor.neverAnswered(2)]) {
    assert.doesNotMatch(message, /[A-Za-z]:\\/, message);
    assert.ok(!message.includes("Users"), message);
  }
});

test("the probe schedule is bounded and backs off", () => {
  const schedule = supervisor.probeSchedule(12);
  assert.equal(schedule.length, 12);
  assert.ok(schedule[0] <= schedule[schedule.length - 1]);
  assert.ok(supervisor.budgetMs(12) > 1000, "gives the interpreter time to import");
  assert.ok(supervisor.budgetMs(12) < 30000, "but gives up rather than hanging on a splash screen");
});

test("the probe schedule is capped even when asked for absurd attempts", () => {
  assert.ok(supervisor.probeSchedule(10000).length <= 40);
  assert.equal(supervisor.probeSchedule(0).length, 12);
  assert.equal(supervisor.probeSchedule(-5).length, 12);
});
