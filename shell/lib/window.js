"use strict";

// WHAT THE WINDOW IS - its frame, its security posture and its overlay floor.
//
// PURE. This builds the options OBJECT that the caller hands to the toolkit. It
// imports nothing, so every one of the security flags below is graded by a test
// that runs with no display server. That matters more here than anywhere else in
// shell/: these are exactly the settings that are wrong by omission, and an
// omitted flag has no line of code for a reviewer to look at.
//
// THE FOUR THAT ARE NOT NEGOTIABLE, and why each one:
//
//   nodeIntegration: false    The page is served over HTTP by another process.
//                             With node integration on, anything that page runs
//                             gets `require`, and the page's content includes a
//                             player nickname fetched from a third-party API.
//   contextIsolation: true    Keeps the preload's context separate from the
//                             page's, so the page cannot reach into the bridge
//                             and rewrite it.
//   sandbox: true             The renderer runs in an OS sandbox.
//   webSecurity: true         Same-origin policy stays on. Turning it off is the
//                             usual "fix" for a fetch that is failing for a
//                             different reason.
//
// A test asserts all four by VALUE rather than by truthiness, so `sandbox: 1`
// would fail even though it is truthy.

/** The preload script's filename, relative to shell/. */
const PRELOAD_FILENAME = "preload.js";

/**
 * Decide whether the window floats above other windows.
 *
 * PRECEDENCE, and it has exactly one home. A flag beats the environment, and the
 * environment beats the remembered preference. This is stated once, here,
 * because a second copy - in the tray's checkbox rendering, say - would be a
 * second answer to the same question, and the two would disagree on the day
 * somebody changed one.
 *
 * @param {object} sources {flag, env, remembered}, any of which may be undefined.
 * @returns {boolean}
 */
function alwaysOnTop(sources) {
  const input = sources && typeof sources === "object" ? sources : {};
  if (typeof input.flag === "boolean") {
    return input.flag;
  }
  // An environment variable is a string. "0" and "false" are both truthy as
  // strings, so they are compared by value rather than coerced.
  if (typeof input.env === "string" && input.env.trim() !== "") {
    const raw = input.env.trim().toLowerCase();
    if (raw === "1" || raw === "true" || raw === "yes") {
      return true;
    }
    if (raw === "0" || raw === "false" || raw === "no") {
      return false;
    }
  }
  if (typeof input.remembered === "boolean") {
    return input.remembered;
  }
  return false;
}

/**
 * Build the browser window options.
 *
 * @param {object} args {bounds, preloadPath, alwaysOnTop, show}
 * @returns {object} Options ready to hand to the toolkit.
 */
function options(args) {
  const input = args && typeof args === "object" ? args : {};
  const bounds = input.bounds ?? {};

  return {
    x: bounds.x,
    y: bounds.y,
    width: bounds.width,
    height: bounds.height,
    minWidth: 360,
    minHeight: 320,

    // Frameless, with the page's own header acting as the drag strip via the
    // -webkit-app-region rule in surface/render.py. An overlay with a title bar
    // wastes a strip of a small window on a caption nobody reads.
    frame: false,
    transparent: false,
    backgroundColor: "#10131a",

    // Off the taskbar: this is a companion, and it is reachable from the tray.
    skipTaskbar: true,
    autoHideMenuBar: true,

    alwaysOnTop: input.alwaysOnTop === true,

    // Shown only once the page has painted, so the operator never sees a white
    // rectangle while the surface is still answering.
    show: input.show === true,

    webPreferences: {
      preload: input.preloadPath,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      experimentalFeatures: false,
    },
  };
}

/**
 * The level at which the window floats.
 *
 * "screen-saver" rather than "floating", because a fullscreen game raises its own
 * window above the normal floating level. This is a companion for a game that is
 * usually running, so the lower level would leave it invisible exactly when it is
 * wanted.
 */
const ALWAYS_ON_TOP_LEVEL = "screen-saver";

module.exports = { ALWAYS_ON_TOP_LEVEL, PRELOAD_FILENAME, alwaysOnTop, options };
