"use strict";

// HOW THE DASHBOARD SURFACE GETS STARTED, decided as data.
//
// The companion is useless without the surface behind it, and requiring the
// operator to start a Python process in a terminal before double-clicking a
// desktop shortcut defeats the point of the shortcut. So the shell starts it.
//
// PURE. This module builds an argv and interprets an exit code. It spawns
// nothing - shell/main.js does that - so the interesting decisions are graded
// without a child process.
//
// ---------------------------------------------------------------------------
// WHY THE CHILD'S OUTPUT IS DISCARDED AND ITS EXIT CODE IS KEPT
// ---------------------------------------------------------------------------
//
// The surface prints a good diagnosis when it refuses to start. Its messages can
// also name a path, and on Windows a path under the user profile CONTAINS THE
// ACCOUNT NAME. This shell renders its own fixed text instead, keyed off the
// child's exit code, which is an integer and is the surface's documented
// contract in surface/server.py's `main` docstring.
//
// The failure this guards against is concrete and Clockspeed measured it: the
// first real shortcut launch of its own shell hit a port left in TIME_WAIT by a
// forced kill moments earlier, the surface exited rather than binding, and the
// operator was told to go read output that had already been thrown away. A
// refusal naming an action the operator cannot perform is worse than one that
// says less.

/** Windows launches Python under a name that varies; the caller picks. */
const DEFAULT_PYTHON = "pythonw.exe";

/**
 * Exit codes the surface documents, mapped to fixed text.
 *
 * A code that is not here renders the generic refusal rather than an
 * interpolated number, because a number the shell cannot explain tells the
 * operator nothing they can act on.
 */
const EXIT_REASONS = new Map([
  [2, "the port it needs is already held by something else"],
]);

const NOT_SPAWNED =
  "ResinCompute: the dashboard could not be started. " +
  "Start it yourself with: python -m surface";

const NEVER_ANSWERED =
  "ResinCompute: the dashboard was started but never answered. " +
  "Start it yourself with: python -m surface and read what it prints.";

const NOT_LOADED =
  "ResinCompute: the dashboard did not load. Is the local surface running?";

/**
 * The argv that starts the surface.
 *
 * A LIST, NEVER A COMMAND STRING. A string would be handed to a shell, and on
 * this machine the shell may be Git Bash, whose MSYS path conversion rewrites
 * arguments before the tool ever sees them. A list argv with shell:false is
 * immune to that, and to quoting entirely.
 *
 * @param {object} args {python, host, port}
 * @returns {string[]}
 */
function spawnArgv(args) {
  const input = args && typeof args === "object" ? args : {};
  const python = typeof input.python === "string" && input.python.trim() ? input.python.trim() : DEFAULT_PYTHON;
  const argv = [python, "-m", "surface"];
  if (typeof input.host === "string" && input.host.trim()) {
    argv.push("--host", input.host.trim());
  }
  if (Number.isInteger(input.port)) {
    argv.push("--port", String(input.port));
  }
  return argv;
}

/**
 * The refusal to show when the surface exited before answering.
 *
 * @param {number|null} exitCode The child's exit code, or null if it was signalled.
 * @returns {string} Fixed text. Never a path, never the child's own output.
 */
function neverAnswered(exitCode) {
  const reason = EXIT_REASONS.get(exitCode);
  if (reason === undefined) {
    return NEVER_ANSWERED;
  }
  return `ResinCompute: the dashboard stopped before answering, because ${reason}.`;
}

/**
 * Delays between readiness probes, in milliseconds.
 *
 * BOUNDED, and the bound is the point. An unbounded retry loop against a surface
 * that will never start is an application that hangs on a splash screen with no
 * diagnosis. Backing off rather than hammering because the common case - the
 * interpreter importing the tree - takes a moment, and ten probes in the first
 * hundred milliseconds all fail for the same uninteresting reason.
 *
 * @param {number} attempts How many probes to make.
 * @returns {number[]} One delay per attempt.
 */
function probeSchedule(attempts) {
  const total = Number.isInteger(attempts) && attempts > 0 ? Math.min(attempts, 40) : 12;
  const schedule = [];
  for (let i = 0; i < total; i += 1) {
    schedule.push(Math.min(150 * 2 ** Math.floor(i / 3), 1500));
  }
  return schedule;
}

/** Total time the schedule allows before giving up, in milliseconds. */
function budgetMs(attempts) {
  return probeSchedule(attempts).reduce((sum, delay) => sum + delay, 0);
}

module.exports = {
  DEFAULT_PYTHON,
  EXIT_REASONS,
  NOT_LOADED,
  NOT_SPAWNED,
  NEVER_ANSWERED,
  budgetMs,
  neverAnswered,
  probeSchedule,
  spawnArgv,
};
