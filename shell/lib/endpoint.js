"use strict";

// WHERE THE DASHBOARD IS. One answer, derived once, from the environment.
//
// PURE, AND IT TAKES THE ENVIRONMENT AS AN ARGUMENT rather than reading
// process.env itself. That is the whole reason the precedence below is testable:
// a module that read the real environment could only be graded by mutating the
// process, and a test that mutates process.env leaks into every test after it.
//
// THE PORT IS NOT A LITERAL IN THIS FILE BY ACCIDENT OF DEFAULTING. It is the
// number ADR-004 assigned, and core/ports.py is its owner on the Python side.
// The duplication across the language boundary is real and is the reason
// tests/test_shell_contract.py exists: it reads THIS file and asserts the number
// matches core.ports.DASHBOARD, so the two cannot drift.

const DEFAULT_HOST = "127.0.0.1";

/** ResinCompute's dashboard port. Owned by core/ports.py - see ADR-004. */
const DEFAULT_PORT = 8791;

const ENV_HOST = "RESIN_DASHBOARD_HOST";
const ENV_PORT = "RESIN_DASHBOARD_PORT";

/** The endpoint could not be resolved from the environment given. */
class EndpointError extends Error {
  constructor(field) {
    // The offending value is carried as a property, not interpolated. An
    // operator-supplied host can be anything, and rendering it into a message
    // that reaches a log or a dialog is how an unaudited string escapes.
    super("the dashboard endpoint could not be resolved from the environment");
    this.name = "EndpointError";
    this.field = field;
  }
}

/**
 * Is this host one that stays on the machine?
 *
 * LOOPBACK ONLY IS A SECURITY BOUNDARY HERE, not a preference. ADR-005 records
 * that the surface serves plain HTTP with no authentication of any kind, and
 * that decision rests entirely on it never being reachable off the box. So a
 * non-loopback host is REFUSED rather than accepted with a warning: a warning
 * printed to a stream nobody reads is not a control.
 */
function isLoopback(host) {
  return host === "127.0.0.1" || host === "localhost" || host === "::1" || host === "[::1]";
}

/**
 * Resolve the dashboard endpoint.
 *
 * Precedence: environment, then the ADR-004 default. There is deliberately no
 * third source - a config file read here would be a second answer to a question
 * core/ports.py already owns.
 *
 * @param {object} env A process environment, or any plain object.
 * @returns {{host: string, port: number, url: string}}
 */
function resolve(env) {
  const source = env && typeof env === "object" ? env : {};

  const host = source[ENV_HOST] ? String(source[ENV_HOST]).trim() : DEFAULT_HOST;
  if (!host) {
    throw new EndpointError(ENV_HOST);
  }
  if (!isLoopback(host)) {
    throw new EndpointError(ENV_HOST);
  }

  let port = DEFAULT_PORT;
  if (source[ENV_PORT] !== undefined && String(source[ENV_PORT]).trim() !== "") {
    const raw = String(source[ENV_PORT]).trim();
    // Number() accepts "0x10", " 12 " and "1e3"; none of those is a port an
    // operator meant to type. Requiring digits only makes the refusal happen
    // here rather than at bind time in another process.
    if (!/^[0-9]+$/.test(raw)) {
      throw new EndpointError(ENV_PORT);
    }
    port = Number(raw);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      throw new EndpointError(ENV_PORT);
    }
  }

  return { host, port, url: `http://${host}:${port}/` };
}

module.exports = {
  DEFAULT_HOST,
  DEFAULT_PORT,
  ENV_HOST,
  ENV_PORT,
  EndpointError,
  isLoopback,
  resolve,
};
