"use strict";

// WHAT IS REMEMBERED BETWEEN LAUNCHES, and nothing else.
//
// Two things: where the window was, and whether it was pinned above other
// windows. Both are conveniences; neither is authoritative, and losing the file
// must degrade to a sensible default rather than to a refusal. An operator whose
// companion refuses to open because a preferences file went missing has a worse
// problem than one whose window opens in the wrong corner.
//
// PURE. This module parses and serialises text. It does NOT read or write the
// file - shell/main.js does that, so every decision here is graded without a
// filesystem.
//
// ---------------------------------------------------------------------------
// THE STRING "false" IS THE WHOLE REASON THIS FILE VALIDATES AT ALL
// ---------------------------------------------------------------------------
//
// The file on disk is JSON that an operator can edit. JSON carries `false` and
// `"false"` as different values, and the second one is TRUTHY in JavaScript. A
// reader that did `Boolean(parsed.alwaysOnTop)` would turn an operator's
// deliberate `"false"` into a pinned window, and the tray checkbox above it
// would then render the opposite of the truth to the only person in a position
// to notice.
//
// So every field is checked by TYPE and a wrong type falls back to the default
// rather than being coerced. Coercion is what makes a wrong value invisible.

/** Shipped defaults, used whenever the file is absent, unreadable or malformed. */
const DEFAULTS = Object.freeze({
  alwaysOnTop: false,
  bounds: null,
});

const BOUNDS_KEYS = Object.freeze(["x", "y", "width", "height"]);

/**
 * Are these bounds four finite integers?
 *
 * NaN and Infinity both survive `typeof === "number"`, and both reach the window
 * toolkit as a size it cannot honour. Number.isInteger rejects all three at once.
 */
function isBounds(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const keys = Object.keys(value);
  if (keys.length !== BOUNDS_KEYS.length) {
    return false;
  }
  return BOUNDS_KEYS.every((key) => Object.hasOwn(value, key) && Number.isInteger(value[key]));
}

/**
 * Parse remembered state out of a JSON string.
 *
 * TOTAL. Never throws. Every failure mode - absent file, empty string, invalid
 * JSON, a JSON array, a field of the wrong type - produces the defaults, because
 * there is no version of "the window position could not be read" that should
 * stop the application starting.
 *
 * @param {string|null|undefined} text The file's contents, or null if absent.
 * @returns {{alwaysOnTop: boolean, bounds: object|null}}
 */
function parse(text) {
  if (typeof text !== "string" || text.trim() === "") {
    return { ...DEFAULTS };
  }

  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { ...DEFAULTS };
  }

  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ...DEFAULTS };
  }

  // typeof, not Boolean(). See the header: "false" is truthy.
  const alwaysOnTop =
    typeof parsed.alwaysOnTop === "boolean" ? parsed.alwaysOnTop : DEFAULTS.alwaysOnTop;

  const bounds = isBounds(parsed.bounds) ? { ...parsed.bounds } : DEFAULTS.bounds;

  return { alwaysOnTop, bounds };
}

/**
 * Serialise remembered state for writing.
 *
 * Writes ONLY the two declared fields, so an unrecognised key an operator added
 * by hand is dropped on the next save rather than being carried forward as
 * something this module might later start honouring by accident.
 *
 * @returns {string} JSON with a trailing newline, ASCII only.
 */
function serialize(state) {
  const safe = parse(typeof state === "string" ? state : JSON.stringify(state ?? {}));
  return `${JSON.stringify(safe, null, 2)}\n`;
}

module.exports = { BOUNDS_KEYS, DEFAULTS, isBounds, parse, serialize };
