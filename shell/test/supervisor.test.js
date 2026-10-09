"use strict";

// Grades the DEGRADED paths of shell/lib/supervisor.js: arguments that are not
// an object, a blank interpreter, blank hosts, a signalled child, exit codes of
// the wrong type, the exact probe schedule and its cap, and the text of every
// refusal. The argv shape, the shell-metacharacter sweep and the path sweep
// are in lib.test.js; nothing here repeats them.
//
// NO QUOTED INTERPRETER NAME APPEARS IN THIS FILE. tests/test_interpreter_pinning.py
// counts them per tracked .js file, so the default is compared through
// supervisor.DEFAULT_PYTHON and the override under test is a name that is not
// an interpreter.
//
// Every test names the supervisor.js line it exercises. The module imports
// nothing, so this runs with no electron binary and spawns no child.

const test = require("node:test");
const assert = require("node:assert/strict");

const supervisor = require("../lib/supervisor.js");

const BARE_ARGV = Object.freeze([supervisor.DEFAULT_PYTHON, "-m", "surface"]);

const ALL_REFUSALS = Object.freeze([
  supervisor.NOT_SPAWNED,
  supervisor.NEVER_ANSWERED,
  supervisor.NOT_LOADED,
  supervisor.neverAnswered(2),
]);

test("arguments that are not an object yield the bare default argv", () => {
  // supervisor.js:67 - `args && typeof args === "object" ? args : {}`. The
  // spawn must still happen when the caller has nothing to say about it.
  for (const bad of [undefined, null, 42, "custom-interp.exe", true]) {
    assert.deepEqual(supervisor.spawnArgv(bad), [...BARE_ARGV], String(bad));
  }
});

test("a blank interpreter falls back to the default and a given one is trimmed", () => {
  // supervisor.js:68 - `typeof input.python === "string" && input.python.trim()`.
  // RESIN_PYTHON exported but empty is the same as RESIN_PYTHON unset, and a
  // value with a stray space must not become a file the loader cannot find.
  for (const blank of ["", "   ", undefined, null, 42]) {
    assert.equal(supervisor.spawnArgv({ python: blank })[0], supervisor.DEFAULT_PYTHON, JSON.stringify(blank));
  }
  assert.equal(supervisor.spawnArgv({ python: "  custom-interp.exe  " })[0], "custom-interp.exe");
});

test("the module flag and module name follow the interpreter whatever else is given", () => {
  // supervisor.js:69 - `[python, "-m", "surface"]`. The surface is started as a
  // module from the repo root, never by a script path, because a path would
  // name a directory and a directory under the profile names the account.
  for (const args of [{}, { host: "localhost", port: 8791 }, { python: "custom-interp.exe" }]) {
    const argv = supervisor.spawnArgv(args);
    assert.equal(argv[1], "-m", JSON.stringify(args));
    assert.equal(argv[2], "surface", JSON.stringify(args));
  }
});

test("a blank host is omitted rather than passed as an empty element", () => {
  // supervisor.js:70-71 - `typeof input.host === "string" && input.host.trim()`.
  // An argv element that is the empty string reaches the surface's argparse as
  // --host with nothing after it and binds nowhere; omitting the flag lets the
  // surface use its own default, which is the correct degraded answer.
  for (const blank of ["", "   ", undefined, null]) {
    const argv = supervisor.spawnArgv({ host: blank });
    assert.ok(!argv.includes("--host"), JSON.stringify(blank));
    assert.ok(argv.every((part) => part.length > 0), JSON.stringify(blank));
  }
  assert.deepEqual(supervisor.spawnArgv({ host: " localhost " }).slice(3), ["--host", "localhost"]);
});

test("an integer port is carried as a digits-only string", () => {
  // supervisor.js:73-74 - `Number.isInteger(input.port)` then String(). The
  // child receives argv strings, and the surface's argparse wants plain digits.
  // A port given as a STRING is not covered here: today :73 drops it silently,
  // which is a finding for a fix rather than a behaviour to pin.
  const argv = supervisor.spawnArgv({ port: 8795 });
  assert.deepEqual(argv.slice(3), ["--port", "8795"]);
  assert.match(argv[4], /^[0-9]+$/);
});

test("a signalled child renders the generic refusal", () => {
  // supervisor.js:85-88 - exitCode is null when the child died to a signal
  // rather than exiting, and main.js:161 initialises its copy to null before
  // the exit event has fired. Map.get(null) is undefined, so the generic text.
  assert.equal(supervisor.neverAnswered(null), supervisor.NEVER_ANSWERED);
  assert.equal(supervisor.neverAnswered(undefined), supervisor.NEVER_ANSWERED);
});

test("exit codes are matched by type, not coerced", () => {
  // supervisor.js:86 - Map.get uses SameValueZero, so the string "2" is not 2,
  // and 0 is not a documented refusal: 0 is a clean shutdown in the surface's
  // exit-code contract, and a clean shutdown before answering still never
  // answered.
  for (const code of ["2", 0, 2.5, -2, true]) {
    assert.equal(supervisor.neverAnswered(code), supervisor.NEVER_ANSWERED, JSON.stringify(code));
  }
});

test("a known-code refusal is one brand-prefixed sentence", () => {
  // supervisor.js:90 - the template. Rendered into a dialog, so it is one
  // sentence, it starts with the brand so the operator knows which app is
  // talking, and it ends with exactly one period.
  const text = supervisor.neverAnswered(2);
  assert.ok(text.startsWith("ResinCompute: "), text);
  assert.ok(text.endsWith("."), text);
  assert.ok(!text.endsWith(".."), text);
  assert.equal(text.indexOf(". "), -1, "one sentence");
  assert.ok(text.includes(supervisor.EXIT_REASONS.get(2)), text);
});

test("the exit reasons map only codes the surface documents", () => {
  // supervisor.js:40-42 against surface/server.py's main docstring: 0 is a
  // clean shutdown, 2 is the port held. 0 needs no reason, so 2 is the only
  // key; every key is a positive integer and every value is a lower-case
  // clause with no digits, so the sentence at :90 reads as one and names no
  // port.
  assert.ok(supervisor.EXIT_REASONS instanceof Map);
  assert.ok(supervisor.EXIT_REASONS.has(2), "the port-held code the surface documents");
  assert.ok(!supervisor.EXIT_REASONS.has(0), "a clean exit is not a refusal reason");
  for (const [code, reason] of supervisor.EXIT_REASONS) {
    assert.ok(Number.isInteger(code) && code > 0, String(code));
    assert.match(reason, /^[a-z][a-z ]*[a-z]$/, reason);
  }
});

test("the schedule is exactly three of each doubling from 150 ms", () => {
  // supervisor.js:105-111 - 150 * 2 ** floor(i / 3). lib.test.js pins the
  // bounds; this pins the values, because the backoff IS the diagnosis budget
  // main.js:170 waits through, and a changed step is a changed wait on a
  // splash screen.
  assert.deepEqual(supervisor.probeSchedule(12), [150, 150, 150, 300, 300, 300, 600, 600, 600, 1200, 1200, 1200]);
  assert.equal(supervisor.budgetMs(12), 6750);
});

test("the schedule never decreases and is capped at 1500 ms for every attempt count", () => {
  // supervisor.js:109 - Math.min(..., 1500). Beyond the fourth triple every
  // probe waits the cap, so forty probes stay under a minute.
  for (let attempts = 1; attempts <= 40; attempts += 1) {
    const schedule = supervisor.probeSchedule(attempts);
    assert.equal(schedule.length, attempts);
    for (let i = 1; i < schedule.length; i += 1) {
      assert.ok(schedule[i] >= schedule[i - 1], `attempts=${attempts} i=${i}`);
    }
    assert.ok(Math.max(...schedule) <= 1500, `attempts=${attempts}`);
  }
  const longest = supervisor.probeSchedule(40);
  assert.equal(longest[longest.length - 1], 1500);
  assert.equal(longest[12], 1500, "the cap is reached at the fifth triple");
  assert.equal(longest[11], 1200, "and not before");
});

test("non-integer attempt counts fall back to the twelve-probe default", () => {
  // supervisor.js:106 - Number.isInteger(attempts) && attempts > 0. lib.test.js
  // covers 0 and a negative; these are the values that are not a count at all.
  for (const bad of [NaN, Infinity, 1.5, undefined, null]) {
    assert.equal(supervisor.probeSchedule(bad).length, 12, String(bad));
  }
});

test("the budget is the sum of the schedule and the longest stays under a minute", () => {
  // supervisor.js:115-117 - reduce over probeSchedule. A budget that drifted
  // from the schedule would make main.js give up early or hang late.
  for (const attempts of [1, 3, 12, 40, 10000]) {
    const schedule = supervisor.probeSchedule(attempts);
    assert.equal(supervisor.budgetMs(attempts), schedule.reduce((sum, delay) => sum + delay, 0), String(attempts));
  }
  assert.equal(supervisor.budgetMs(40), 48750);
  assert.ok(supervisor.budgetMs(10000) < 60000, "forty probes is under a minute");
});

test("every refusal is 7-bit ASCII, brand-prefixed and carries no digit", () => {
  // supervisor.js:44-53 and :90 - fixed text that reaches a dialog. ASCII
  // because the glyph gate sweeps this tree; brand-prefixed because the dialog
  // appears before any window names the app; digit-free because a host or
  // port in a refusal is a value the shell would then be vouching for.
  assert.equal(ALL_REFUSALS.length, 4);
  for (const text of ALL_REFUSALS) {
    for (const char of text) {
      assert.ok(char.charCodeAt(0) < 0x80, `non-ASCII in: ${text}`);
    }
    assert.ok(text.startsWith("ResinCompute: "), text);
    assert.doesNotMatch(text, /[0-9]/, text);
  }
});

test("the refusals that tell the operator what to run name the module, not a path", () => {
  // supervisor.js:46 and :50 - the module invocation. The one thing the
  // operator can do is start the surface by hand, and the instruction names
  // the module because a script path would name a directory.
  assert.match(supervisor.NOT_SPAWNED, /-m surface/);
  assert.match(supervisor.NEVER_ANSWERED, /-m surface/);
});
