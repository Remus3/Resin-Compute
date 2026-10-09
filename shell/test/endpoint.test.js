"use strict";

// Grades the DEGRADED paths of shell/lib/endpoint.js: an environment that is
// not an object, blank values, untrimmed values, the negative side of the
// loopback check, and the shape of a refusal. The happy path and the refusals
// themselves are in lib.test.js; nothing here repeats them.
//
// Every test names the endpoint.js line it exercises. The module imports
// nothing, so this runs with no electron binary and no display server.

const test = require("node:test");
const assert = require("node:assert/strict");

const endpoint = require("../lib/endpoint.js");

const DEFAULTS = Object.freeze({
  host: endpoint.DEFAULT_HOST,
  port: endpoint.DEFAULT_PORT,
  url: `http://${endpoint.DEFAULT_HOST}:${endpoint.DEFAULT_PORT}/`,
});

test("a non-object environment yields the defaults rather than a crash", () => {
  // endpoint.js:64 - `env && typeof env === "object" ? env : {}`. main.js hands
  // over process.env, but a caller with no environment at all must still get
  // an answer, not a TypeError from reading a property of null.
  for (const env of [null, undefined, 42, "text", true]) {
    assert.deepEqual(endpoint.resolve(env), DEFAULTS, String(env));
  }
});

test("an empty host and an empty port both fall back to the defaults", () => {
  // endpoint.js:66 - an empty string is falsy, so the host falls to
  // DEFAULT_HOST. endpoint.js:75 - an empty port trims to "", so the port
  // falls to DEFAULT_PORT. An exported-but-empty variable is how a shell
  // script unsets a value, and it must read as unset.
  assert.deepEqual(endpoint.resolve({ RESIN_DASHBOARD_HOST: "", RESIN_DASHBOARD_PORT: "" }), DEFAULTS);
  assert.deepEqual(endpoint.resolve({ RESIN_DASHBOARD_HOST: "" }), DEFAULTS);
  assert.deepEqual(endpoint.resolve({ RESIN_DASHBOARD_PORT: "" }), DEFAULTS);
});

test("the host is trimmed before the loopback check", () => {
  // endpoint.js:66 - String(...).trim(). A value pasted with a trailing space
  // is the same host, and refusing it would read as a refusal of loopback.
  const resolved = endpoint.resolve({ RESIN_DASHBOARD_HOST: " localhost " });
  assert.equal(resolved.host, "localhost");
  assert.equal(resolved.url, `http://localhost:${endpoint.DEFAULT_PORT}/`);
});

test("a port given as a number rather than a string is still read", () => {
  // endpoint.js:75-76 - String(source[ENV_PORT]). A real environment carries
  // strings only, but the parameter is any plain object, and a number is the
  // natural thing for a launcher or a test to put there.
  assert.equal(endpoint.resolve({ RESIN_DASHBOARD_PORT: 8795 }).port, 8795);
});

test("the port range is inclusive at both ends", () => {
  // endpoint.js:84 - `port < 1 || port > 65535`. lib.test.js refuses 0 and
  // 65536; this pins the two values just inside.
  assert.equal(endpoint.resolve({ RESIN_DASHBOARD_PORT: "1" }).port, 1);
  assert.equal(endpoint.resolve({ RESIN_DASHBOARD_PORT: "65535" }).port, 65535);
});

test("every accepted spelling yields a URL the platform parses", () => {
  // endpoint.js:89 - the url template. main.js appends "health" to it and hands
  // the result to net.request, so a url that new URL() rejects is a degraded
  // path the shell cannot recover from. This list IS the accepted set: since
  // isLoopback at :50 shrank to the two spellings the AF_INET surface can bind,
  // no accepted host builds a url new URL() refuses. The bare "::1" used to be
  // accepted and did exactly that; it is now refused, and the refusal arm
  // below pins it.
  for (const host of ["127.0.0.1", "localhost"]) {
    const resolved = endpoint.resolve({ RESIN_DASHBOARD_HOST: host });
    const parsed = new URL(resolved.url);
    assert.equal(parsed.protocol, "http:", host);
    assert.equal(parsed.port, String(endpoint.DEFAULT_PORT), host);
    assert.equal(parsed.pathname, "/", host);
    assert.equal(new URL("health", resolved.url).pathname, "/health", host);
  }
});

test("isLoopback is exact - case, neighbours and non-strings are all refused", () => {
  // endpoint.js:50 - two strict equalities and nothing else. "LOCALHOST" is
  // the same machine to a resolver but not to this check, and that is the
  // intended side of the error: the check guards ADR-005's no-authentication
  // decision, so it refuses anything it cannot prove.
  for (const host of ["LOCALHOST", "127.0.0.2", "127.0.0.1 ", "::2", "", "0.0.0.0", null, undefined, 127, ["127.0.0.1"]]) {
    assert.equal(endpoint.isLoopback(host), false, String(host));
  }
});

test("the two IPv6 loopback spellings are refused, not accepted and then broken", () => {
  // endpoint.js:50 - isLoopback names exactly the two spellings the surface can
  // answer on. surface/server.py:282 binds through ThreadingHTTPServer, whose
  // address_family is AF_INET, so HTTPServer(("::1", 0)) raises gaierror and
  // HTTPServer(("[::1]", 0)) raises gaierror (errno -9 and -2 on Linux; the
  // numbers differ by platform) - neither spelling can ever be served.
  // Before the fix both were accepted: the bare form built
  // http://::1:8791/, which new URL() rejects with ERR_INVALID_URL inside the
  // net.request at main.js:119 with no catch above it, and the bracketed form
  // parsed but drove the surface to exit 2, which the shell reports as a held
  // port. Refusing both routes them into the EXISTING ENDPOINT_UNRESOLVED
  // dialog at main.js:332-335, which names the variable and never the value.
  for (const host of ["::1", "[::1]"]) {
    assert.equal(endpoint.isLoopback(host), false, host);
    let caught = null;
    try {
      endpoint.resolve({ RESIN_DASHBOARD_HOST: host });
    } catch (error) {
      caught = error;
    }
    assert.ok(caught instanceof endpoint.EndpointError, `${host} is refused`);
    assert.equal(caught.field, endpoint.ENV_HOST, host);
  }
});

test("a refusal is an Error that names the offending field as a property", () => {
  // endpoint.js:25-34 - EndpointError. The field travels as `.field` so a
  // caller can say WHICH variable to check without this module ever rendering
  // the value itself. lib.test.js pins the non-interpolation; this pins the
  // shape the caller relies on.
  for (const [env, field] of [
    [{ RESIN_DASHBOARD_HOST: "example.com" }, endpoint.ENV_HOST],
    [{ RESIN_DASHBOARD_PORT: "abc" }, endpoint.ENV_PORT],
    [{ RESIN_DASHBOARD_PORT: "0" }, endpoint.ENV_PORT],
  ]) {
    let caught = null;
    try {
      endpoint.resolve(env);
    } catch (error) {
      caught = error;
    }
    assert.ok(caught instanceof Error, "refusal is an Error");
    assert.ok(caught instanceof endpoint.EndpointError, "refusal is an EndpointError");
    assert.equal(caught.name, "EndpointError");
    assert.equal(caught.field, field);
    assert.equal(typeof caught.message, "string");
    assert.ok(caught.message.length > 0);
  }
});

test("the exported variable names are the ones resolve reads", () => {
  // endpoint.js:21-22 - ENV_HOST and ENV_PORT. Every other test spells the
  // names out; this one goes through the exports, so a rename that forgot
  // either side is caught here rather than in a launcher that set a variable
  // nobody reads.
  assert.notEqual(endpoint.ENV_HOST, endpoint.ENV_PORT);
  assert.equal(endpoint.resolve({ [endpoint.ENV_PORT]: "8795" }).port, 8795);
  assert.equal(endpoint.resolve({ [endpoint.ENV_HOST]: "localhost" }).host, "localhost");
  assert.throws(() => endpoint.resolve({ [endpoint.ENV_HOST]: "example.com" }), endpoint.EndpointError);
});

test("resolving does not mutate the environment it is given", () => {
  // endpoint.js:63-89 - every access is a read. A frozen object throws on any
  // write under "use strict", so this is a hard check, not a comparison.
  const env = Object.freeze({ RESIN_DASHBOARD_HOST: "localhost", RESIN_DASHBOARD_PORT: "8795" });
  assert.deepEqual(endpoint.resolve(env), { host: "localhost", port: 8795, url: "http://localhost:8795/" });
});
