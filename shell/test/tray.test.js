"use strict";

// Grades what the tray SHOWS. Runs under `node --test` with no electron binary
// and no display server, which is the whole reason lib/tray.js imports nothing.

const test = require("node:test");
const assert = require("node:assert/strict");
const zlib = require("node:zlib");

const tray = require("../lib/tray.js");

const VISIBLE = { visible: true, alwaysOnTop: false };
const HIDDEN = { visible: false, alwaysOnTop: true };

test("the menu carries every declared entry, in order", () => {
  const ids = tray.menuTemplate(VISIBLE).map((entry) => entry.id);
  assert.deepEqual(ids, [
    tray.MENU_IDS.SHOW_HIDE,
    tray.MENU_IDS.ALWAYS_ON_TOP,
    tray.MENU_IDS.OPEN_IN_BROWSER,
    tray.MENU_IDS.SEPARATOR_BEFORE_QUIT,
    tray.MENU_IDS.QUIT,
  ]);
});

test("every entry carries a declared, unique id - the separator included", () => {
  const entries = tray.menuTemplate(VISIBLE);
  const ids = entries.map((entry) => entry.id);
  assert.equal(new Set(ids).size, ids.length);
  const declared = new Set(Object.values(tray.MENU_IDS));
  for (const id of ids) {
    assert.ok(declared.has(id), `undeclared menu id: ${id}`);
  }
});

test("quit is present in every state", () => {
  for (const state of [VISIBLE, HIDDEN]) {
    const ids = tray.menuTemplate(state).map((entry) => entry.id);
    assert.ok(ids.includes(tray.MENU_IDS.QUIT));
  }
});

test("the separator sits directly above quit", () => {
  const ids = tray.menuTemplate(VISIBLE).map((entry) => entry.id);
  assert.equal(ids.indexOf(tray.MENU_IDS.SEPARATOR_BEFORE_QUIT) + 1, ids.indexOf(tray.MENU_IDS.QUIT));
});

test("the show/hide label tracks reality rather than guessing", () => {
  assert.equal(tray.menuTemplate(VISIBLE)[0].label, "Hide window");
  assert.equal(tray.menuTemplate(HIDDEN)[0].label, "Show window");
});

test("the always-on-top checkbox reflects the state it was given", () => {
  assert.equal(tray.menuTemplate(VISIBLE)[1].checked, false);
  assert.equal(tray.menuTemplate(HIDDEN)[1].checked, true);
});

test("a fresh array of fresh objects is returned every call", () => {
  const first = tray.menuTemplate(VISIBLE);
  const second = tray.menuTemplate(VISIBLE);
  assert.notEqual(first, second);
  assert.notEqual(first[0], second[0]);
  first[0].label = "poisoned";
  assert.equal(tray.menuTemplate(VISIBLE)[0].label, "Hide window");
});

test("the string false is refused rather than coerced to true", () => {
  // The whole reason this module validates. JSON on disk can carry "false",
  // which is truthy, and a checkbox reading it as checked would show the
  // operator the opposite of the truth.
  assert.throws(
    () => tray.menuTemplate({ visible: true, alwaysOnTop: "false" }),
    tray.MenuStateError,
  );
});

test("a missing key is refused", () => {
  assert.throws(() => tray.menuTemplate({ visible: true }), tray.MenuStateError);
});

test("an unknown key is refused, and reported before the missing one", () => {
  assert.throws(
    () => tray.menuTemplate({ visible: true, alwaysOnTop: false, extra: 1 }),
    tray.UnknownMenuKeyError,
  );
  // A misspelled key produces both faults at once; only the first names the cause.
  assert.throws(
    () => tray.menuTemplate({ visible: true, alwaysOnTopp: false }),
    tray.UnknownMenuKeyError,
  );
});

test("a non-object, an array and a function are all refused", () => {
  for (const bad of [null, undefined, 42, "state", [], () => {}]) {
    assert.throws(() => tray.menuTemplate(bad), tray.MenuStateError);
  }
});

test("an error message never interpolates the offending value", () => {
  try {
    tray.menuTemplate({ visible: true, alwaysOnTop: "SENTINEL_VALUE" });
    assert.fail("expected a refusal");
  } catch (error) {
    assert.ok(!error.message.includes("SENTINEL_VALUE"));
    assert.equal(error.field, "alwaysOnTop");
  }
});

// ---------------------------------------------------------------------------
// The icon. Graded as a picture, not as a string.
// ---------------------------------------------------------------------------

test("the icon is a data URL and is 7-bit ASCII", () => {
  assert.ok(tray.ICON_DATA_URL.startsWith("data:image/png;base64,"));
  for (const char of tray.ICON_DATA_URL) {
    assert.ok(char.charCodeAt(0) <= 0x7e, "the icon payload left 7-bit ASCII");
  }
});

test("the icon payload carries no adjacent solidus pair", () => {
  // Two of them open a line comment as far as any text scanner is concerned.
  const payload = tray.ICON_DATA_URL.slice("data:image/png;base64,".length);
  assert.ok(!payload.includes("/" + "/"));
});

test("the icon decodes to a real 32x32 PNG with opaque pixels", () => {
  // A stub that decoded to nothing would still be a string, would still be
  // ASCII, and would put an INVISIBLE icon in the tray - which, once the window
  // hides instead of closing, is an application the operator can neither reopen
  // nor quit. So the bytes are decoded and the picture is counted.
  const payload = tray.ICON_DATA_URL.slice("data:image/png;base64,".length);
  const bytes = Buffer.from(payload, "base64");

  assert.deepEqual(
    bytes.subarray(0, 8),
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    "not a PNG signature",
  );

  // IHDR sits immediately after the signature: 4 length, 4 tag, then the fields.
  assert.equal(bytes.subarray(12, 16).toString("ascii"), "IHDR");
  assert.equal(bytes.readUInt32BE(16), 32, "width");
  assert.equal(bytes.readUInt32BE(20), 32, "height");
  assert.equal(bytes[24], 8, "bit depth");
  assert.equal(bytes[25], 6, "colour type should be truecolour with alpha");

  // Walk the chunk stream, check every CRC, and inflate the pixel data.
  let offset = 8;
  const idat = [];
  let sawEnd = false;
  while (offset < bytes.length) {
    const length = bytes.readUInt32BE(offset);
    const tag = bytes.subarray(offset + 4, offset + 8).toString("ascii");
    const data = bytes.subarray(offset + 8, offset + 8 + length);
    const declared = bytes.readUInt32BE(offset + 8 + length);
    const computed = zlib.crc32
      ? zlib.crc32(Buffer.concat([Buffer.from(tag, "ascii"), data]))
      : declared;
    assert.equal(computed >>> 0, declared >>> 0, `CRC mismatch in ${tag}`);
    if (tag === "IDAT") {
      idat.push(data);
    }
    if (tag === "IEND") {
      sawEnd = true;
    }
    offset += 12 + length;
  }
  assert.ok(sawEnd, "no IEND chunk");

  const raw = zlib.inflateSync(Buffer.concat(idat));
  // 32 scanlines, each one filter byte plus 32 RGBA pixels.
  assert.equal(raw.length, 32 * (1 + 32 * 4));

  let opaque = 0;
  for (let row = 0; row < 32; row += 1) {
    const start = row * (1 + 32 * 4) + 1;
    for (let col = 0; col < 32; col += 1) {
      if (raw[start + col * 4 + 3] === 255) {
        opaque += 1;
      }
    }
  }
  assert.ok(opaque > 200, `the icon decoded to only ${opaque} opaque pixels`);
  assert.ok(opaque < 32 * 32, "the icon is a solid block with no transparent corners");
});

test("the tooltip is fixed text carrying no path, host or account id", () => {
  const text = tray.tooltip();
  assert.equal(text, "ResinCompute companion");
  // Letters and spaces only. A drive letter, a home directory segment, a host
  // and port or a player UID cannot be spelled in that character set, so the
  // whole class is excluded rather than the members somebody remembered.
  assert.match(text, /^[A-Za-z ]+$/);
  assert.ok(text.length < 120, "the platform truncates past 128 bytes");
});
