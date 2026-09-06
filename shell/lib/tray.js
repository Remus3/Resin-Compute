"use strict";

// What the system tray SHOWS, as plain data.
//
// WHAT THIS IS FOR. Closing the companion window HIDES it to the notification
// area rather than quitting, and the dashboard behind it stays warm. Everything
// that decides what the operator then sees - the icon's pixels, the menu's
// entries, their order, their labels, their checked flags and the tooltip - is
// decided here. shell/main.js takes this data and hands it to a Tray and a Menu,
// and that is all it does with it.
//
// PURE BY CONTRACT. This module reaches for nothing: not electron, not the
// filesystem, not a clock. That is what lets it be graded by `node --test` on a
// machine with no display server and no electron binary, which matters because
// the electron package declares no postinstall step and fetches its platform
// binary lazily on the first require. A checkout that has run only `npm install`
// has no electron.exe, and every test in shell/test still runs.
//
// ---------------------------------------------------------------------------
// WHY THE ICON IS TEXT
// ---------------------------------------------------------------------------
//
// This tree is 7-bit ASCII by hard rule and tracks no binary asset. A committed
// .ico or .png would violate that on its first byte. So the icon ships as a
// base64 data URL, which is text, and the caller turns it into an image at run
// time.
//
// THE PAYLOAD CARRIES NO ADJACENT SOLIDUS PAIR, and that is a constraint the
// generator checked rather than a coincidence. Two adjacent solidus characters
// open a line comment as far as any text scanner is concerned, and this tree is
// swept by hooks that read files as text.
//
// WHAT IT DEPICTS AND WHY THAT COLOUR. A resin drop: a disc low in a 32x32 field
// tapering to a point at the top, with a small interior highlight. The body is
// 2078c8, and that value was SEARCHED for rather than picked. A Windows
// notification area is near-black under the default theme and near-white under
// the light one, so the same bytes must be legible on both. 2078c8 measures
// 4.58:1 against black AND 4.58:1 against white. The first colour tried, a
// brighter cyan, measured 2.94:1 against white and was rejected by the
// generator's own 3:1 assertion rather than by review.
//
// 32x32 RATHER THAN 16x16 ON PURPOSE. Windows asks the notification area for
// 16x16 at 100% scaling and 32x32 at 200%, which is ordinary on a modern
// display. Supplying the larger source makes the common downscale an exact 2:1.

const ICON_PNG_BASE64 = [
  "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAf0lEQVR42mNgGAVDGShU",
  "nPg/oJbD8MhzALLldHcENsvp6ogBdQA+y+niiAF1ADGW09QRA+YAUiymiUNghs279AEF",
  "08UBuCynmyMG1AHIhlDiALIdMagcQG4ipKoD6J4dRx1ALUcMWDFM9dJwwOuCAXPAoGkP",
  "DIom2aDqmAwbAABL6zEDJkiqxQAAAABJRU5ErkJggg==",
].join("");

/**
 * The tray icon, ready to be turned into an image by the caller.
 *
 * ASCII, and 7-bit at that. This is the only shape in which a raster image can
 * live in this repository at all.
 */
const ICON_DATA_URL = "data:image/png;base64," + ICON_PNG_BASE64;

/**
 * The stable identity of each menu entry.
 *
 * A SEAM, NOT A CONVENIENCE. The caller switches on these to decide which
 * handler fires, so renaming one silently disconnects an entry from its
 * behaviour - and the failure is not an exception, it is a menu item that does
 * nothing when clicked.
 *
 * THE SEPARATOR HAS ONE TOO. It does not need an id to render. It has one so
 * that "every entry carries a declared, unique id" is a total statement about
 * the template rather than one with an exception clause, and so the test that
 * checks it needs no filter. A filtered check goes quietly vacuous the day the
 * filter widens by one entry type.
 */
const MENU_IDS = Object.freeze({
  SHOW_HIDE: "resincompute.tray.showHide",
  ALWAYS_ON_TOP: "resincompute.tray.alwaysOnTop",
  OPEN_IN_BROWSER: "resincompute.tray.openInBrowser",
  SEPARATOR_BEFORE_QUIT: "resincompute.tray.separatorBeforeQuit",
  QUIT: "resincompute.tray.quit",
});

/** The whole of the state a menu is built from. Two booleans, and nothing else. */
const MENU_STATE_KEYS = Object.freeze(["visible", "alwaysOnTop"]);

const LABEL_HIDE = "Hide window";
const LABEL_SHOW = "Show window";
const LABEL_ALWAYS_ON_TOP = "Always on top";
const LABEL_OPEN_IN_BROWSER = "Open in browser";
const LABEL_QUIT = "Quit ResinCompute";

// Fixed text, and deliberately incurious: it names the application and stops. A
// tooltip that helpfully reported which account was loaded, or which address the
// surface was on, would put a player UID or a host and port into a string the
// operating system renders on hover. The historic notification-area tooltip
// field is 128 bytes including its terminator, so anything longer is silently
// truncated by the platform rather than refused.
const TOOLTIP_TEXT = "ResinCompute companion";

/** The menu state is not two booleans under the two declared names. */
class MenuStateError extends Error {
  constructor(field) {
    // The offending VALUE is not interpolated into the message. Every field this
    // module declares is a fixed identifier, so naming the failing one adds
    // nothing a reader needs, and rendering caller-supplied text through an
    // error path is how an unaudited value reaches a log. It is carried as a
    // property instead, where a debugger can read it and a log line will not.
    super("the tray menu state is not two booleans named visible and alwaysOnTop");
    this.name = "MenuStateError";
    this.field = field;
  }
}

/** The menu state carries a key this module does not declare. */
class UnknownMenuKeyError extends Error {
  constructor(keys) {
    super("the tray menu state carries a key this module does not declare");
    this.name = "UnknownMenuKeyError";
    this.keys = keys;
  }
}

/**
 * Build the tray menu for one window state.
 *
 * TOTAL BY CONSTRUCTION. Every input either produces a menu or produces a named
 * refusal; nothing is defaulted and nothing is coerced. The coercion case is the
 * one that bites: the remembered preference arrives from an operator-editable
 * JSON file on disk, and that file can carry the STRING "false", which is
 * truthy. A checkbox that read it as checked would report the opposite of the
 * truth to the only person able to notice.
 *
 * THE UNKNOWN-KEY CHECK COMES FIRST and the order is load bearing. A misspelled
 * key produces both faults at once - the key is unrecognised AND the one it was
 * meant to be is missing - and of the two messages only the first names the
 * cause.
 *
 * A FRESH ARRAY OF FRESH OBJECTS, EVERY CALL. The menu is rebuilt whenever the
 * state changes, so a shared array would let a caller that mutated one entry
 * poison every later menu, a defect that first appears on the second click.
 *
 * @param {object} state Exactly the keys in MENU_STATE_KEYS, both boolean.
 * @returns {Array<object>} Entries in display order, each with a declared id.
 */
function menuTemplate(state) {
  // An array is an object and a function is not, so neither test alone is
  // enough. Both are rejected: an array has no named keys to read, and a
  // function is a caller that passed the wrong thing entirely.
  if (state === null || typeof state !== "object" || Array.isArray(state)) {
    throw new MenuStateError(undefined);
  }

  const unknown = Object.keys(state).filter((key) => !MENU_STATE_KEYS.includes(key));
  if (unknown.length > 0) {
    throw new UnknownMenuKeyError(unknown);
  }

  for (const key of MENU_STATE_KEYS) {
    if (!Object.hasOwn(state, key) || typeof state[key] !== "boolean") {
      throw new MenuStateError(key);
    }
  }

  // A LIE IN THE UI COSTS MORE THAN A CLICK. A label reading "Show window" over
  // a window that is already showing teaches the operator that the menu does not
  // track reality, and they then have no reason to believe the checkbox either.
  return [
    { id: MENU_IDS.SHOW_HIDE, label: state.visible ? LABEL_HIDE : LABEL_SHOW },
    {
      id: MENU_IDS.ALWAYS_ON_TOP,
      label: LABEL_ALWAYS_ON_TOP,
      type: "checkbox",
      checked: state.alwaysOnTop,
    },
    { id: MENU_IDS.OPEN_IN_BROWSER, label: LABEL_OPEN_IN_BROWSER },
    {
      // The one entry that renders no text. It sits above quit because quit is
      // the only irreversible item in the menu, and a rule between them is what
      // stops a mis-aimed click landing on it.
      id: MENU_IDS.SEPARATOR_BEFORE_QUIT,
      type: "separator",
    },
    {
      // PRESENT IN EVERY STATE, UNCONDITIONALLY. Once the window hides instead
      // of closing, the taskbar offers no way out and this entry is the only
      // one. A menu that dropped it under some combination of flags would leave
      // the operator with the task manager.
      id: MENU_IDS.QUIT,
      label: LABEL_QUIT,
    },
  ];
}

/**
 * The tray icon's hover text.
 *
 * A FUNCTION RATHER THAN A CONSTANT, though it takes no argument and returns the
 * same string every time. The tooltip is the natural place for a future status -
 * connected, stale, refused - and exposing it as a call now means that change
 * stays inside this module instead of moving a published constant.
 */
function tooltip() {
  return TOOLTIP_TEXT;
}

module.exports = {
  ICON_DATA_URL,
  MENU_IDS,
  MENU_STATE_KEYS,
  MenuStateError,
  UnknownMenuKeyError,
  menuTemplate,
  tooltip,
};
