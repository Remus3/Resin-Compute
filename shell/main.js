"use strict";

// The Electron main process.
//
// WIRING ONLY. Every decision this file appears to make was made somewhere
// testable and is only being carried here: where the surface is is endpoint.js,
// what is remembered between launches is state.js, where the window opens is
// geometry.js, what the window IS - its frame, its floor and its security
// posture - is window.js, what the tray shows is tray.js, and how the surface is
// started is supervisor.js. None of those can be graded with Electron in the
// way, which is exactly why none of them live here.
//
// WHY THE RULE IS NOT STYLE. Because this file imports Electron, nothing can
// load it, so nothing in shell/test grades a single line below. Sibling-A
// records what that costs: its certificate verdict map lived in its own main.js,
// no test could reach it, and changing it to a blanket accept left the whole
// gate green. Anything here that starts making a choice belongs in lib/.
//
// WHAT IS LEFT is the part that cannot be tested without a display server, and
// it is deliberately the least interesting part.

const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const { app, BrowserWindow, Menu, Tray, dialog, nativeImage, net, screen, shell } = require("electron");

const endpoint = require("./lib/endpoint.js");
const geometry = require("./lib/geometry.js");
const stateLib = require("./lib/state.js");
const supervisor = require("./lib/supervisor.js");
const trayLib = require("./lib/tray.js");
const windowLib = require("./lib/window.js");

// ---------------------------------------------------------------------------
// Refusals - fixed text, and never a path
// ---------------------------------------------------------------------------
//
// A path under the user profile carries the Windows account name, so no message
// below quotes one. shell/test/lib.test.js pins that for the supervisor's set.

const ENDPOINT_UNRESOLVED =
  "ResinCompute: the dashboard endpoint could not be resolved. " +
  "Check RESIN_DASHBOARD_HOST and RESIN_DASHBOARD_PORT.";

const STATE_NOT_SAVED = "ResinCompute: the window position could not be saved.";

// showErrorBox rather than the async dialog, because these run BEFORE any window
// exists and several run before app.whenReady has resolved. The console line is
// kept as well: a terminal launch is still supported and is the better
// diagnostic. A desktop shortcut has no terminal attached, so without the dialog
// the operator double-clicks an icon and gets silence.
function refuse(message) {
  console.error(message);
  try {
    dialog.showErrorBox("ResinCompute", message);
  } catch {
    // A dialog before the app is ready can itself fail. The console line above
    // has already been written, so there is nothing further to try.
  }
  app.exit(1);
}

// ---------------------------------------------------------------------------
// Process-wide handles
// ---------------------------------------------------------------------------

let mainWindow = null;
let tray = null;
let surfaceChild = null;
let quitting = false;
let target = null;
let remembered = stateLib.DEFAULTS;

const STATE_FILENAME = "window-state.json";

function statePath() {
  return path.join(app.getPath("userData"), STATE_FILENAME);
}

function readState() {
  try {
    return stateLib.parse(fs.readFileSync(statePath(), "utf8"));
  } catch {
    // Absent or unreadable is not an error. state.parse is total and its
    // defaults are the right answer for a first launch.
    return stateLib.parse(null);
  }
}

function writeState() {
  if (mainWindow === null || mainWindow.isDestroyed()) {
    return;
  }
  try {
    const payload = stateLib.serialize({
      alwaysOnTop: mainWindow.isAlwaysOnTop(),
      bounds: mainWindow.getBounds(),
    });
    fs.mkdirSync(app.getPath("userData"), { recursive: true });
    // Atomic: write a sibling temp then rename, matching core/atomic_io.py. A
    // reader that polled mid-write would otherwise see a truncated file.
    const tmp = `${statePath()}.tmp`;
    fs.writeFileSync(tmp, payload, "utf8");
    fs.renameSync(tmp, statePath());
  } catch {
    // Never fatal, and never quotes the path. Losing a window position is a
    // worse outcome than the application refusing to close.
    console.error(STATE_NOT_SAVED);
  }
}

// ---------------------------------------------------------------------------
// The surface child process
// ---------------------------------------------------------------------------

function surfaceAnswered() {
  return new Promise((resolve) => {
    const request = net.request({ method: "GET", url: `${target.url}health` });
    request.on("response", (response) => {
      response.on("data", () => {});
      response.on("end", () => resolve(response.statusCode === 200));
    });
    request.on("error", () => resolve(false));
    request.end();
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function ensureSurface() {
  if (await surfaceAnswered()) {
    // Already running - an operator with `python -m surface` in a terminal, or a
    // second launch while the first is still up. Adopt it rather than starting a
    // rival that would fail to bind and look like a broken application.
    return true;
  }

  const argv = supervisor.spawnArgv({
    python: process.env.RESIN_PYTHON,
    host: target.host,
    port: target.port,
  });

  try {
    surfaceChild = spawn(argv[0], argv.slice(1), {
      cwd: path.join(__dirname, ".."),
      // The child's OUTPUT is discarded and its exit CODE is kept. Its messages
      // can name a path; the code is an integer and is its documented contract.
      stdio: "ignore",
      windowsHide: true,
      shell: false,
    });
  } catch {
    refuse(supervisor.NOT_SPAWNED);
    return false;
  }

  let exitCode = null;
  surfaceChild.on("exit", (code) => {
    exitCode = code;
    surfaceChild = null;
  });
  surfaceChild.on("error", () => {
    surfaceChild = null;
  });

  for (const delay of supervisor.probeSchedule(12)) {
    await sleep(delay);
    if (await surfaceAnswered()) {
      return true;
    }
  }

  refuse(supervisor.neverAnswered(exitCode));
  return false;
}

// ---------------------------------------------------------------------------
// Window and tray
// ---------------------------------------------------------------------------

function rebuildTrayMenu() {
  if (tray === null || mainWindow === null || mainWindow.isDestroyed()) {
    return;
  }

  const template = trayLib.menuTemplate({
    visible: mainWindow.isVisible(),
    alwaysOnTop: mainWindow.isAlwaysOnTop(),
  });

  // The ids are the seam. Switching on them here is what connects each entry to
  // its behaviour, and it is why tray.js gives even the separator one.
  const withHandlers = template.map((entry) => {
    switch (entry.id) {
      case trayLib.MENU_IDS.SHOW_HIDE:
        return { ...entry, click: toggleWindow };
      case trayLib.MENU_IDS.ALWAYS_ON_TOP:
        return { ...entry, click: toggleAlwaysOnTop };
      case trayLib.MENU_IDS.OPEN_IN_BROWSER:
        return { ...entry, click: () => shell.openExternal(target.url) };
      case trayLib.MENU_IDS.QUIT:
        return { ...entry, click: quitForReal };
      default:
        return entry;
    }
  });

  tray.setContextMenu(Menu.buildFromTemplate(withHandlers));
}

function toggleWindow() {
  if (mainWindow === null || mainWindow.isDestroyed()) {
    return;
  }
  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
  rebuildTrayMenu();
}

function toggleAlwaysOnTop() {
  if (mainWindow === null || mainWindow.isDestroyed()) {
    return;
  }
  const next = !mainWindow.isAlwaysOnTop();
  mainWindow.setAlwaysOnTop(next, windowLib.ALWAYS_ON_TOP_LEVEL);
  writeState();
  rebuildTrayMenu();
}

function quitForReal() {
  quitting = true;
  writeState();
  if (surfaceChild !== null) {
    surfaceChild.kill();
    surfaceChild = null;
  }
  app.quit();
}

function createTray() {
  const image = nativeImage.createFromDataURL(trayLib.ICON_DATA_URL);
  tray = new Tray(image);
  tray.setToolTip(trayLib.tooltip());
  tray.on("click", toggleWindow);
  rebuildTrayMenu();
}

function createWindow() {
  const workArea = screen.getPrimaryDisplay().workArea;
  const bounds = geometry.place(remembered.bounds, workArea);
  const onTop = windowLib.alwaysOnTop({
    env: process.env.RESIN_ALWAYS_ON_TOP,
    remembered: remembered.alwaysOnTop,
  });

  mainWindow = new BrowserWindow(
    windowLib.options({
      bounds,
      preloadPath: path.join(__dirname, windowLib.PRELOAD_FILENAME),
      alwaysOnTop: onTop,
      show: false,
    }),
  );

  if (onTop) {
    mainWindow.setAlwaysOnTop(true, windowLib.ALWAYS_ON_TOP_LEVEL);
  }

  // CLOSING HIDES. This is the behaviour the tray exists for, and it is also why
  // the quit entry is unconditional: once the window hides instead of closing,
  // the taskbar offers no way out.
  mainWindow.on("close", (event) => {
    if (!quitting) {
      event.preventDefault();
      mainWindow.hide();
      rebuildTrayMenu();
    }
  });

  mainWindow.on("moved", writeState);
  mainWindow.on("resized", writeState);
  mainWindow.on("show", rebuildTrayMenu);
  mainWindow.on("hide", rebuildTrayMenu);

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    rebuildTrayMenu();
  });

  mainWindow.webContents.on("did-fail-load", () => {
    console.error(supervisor.NOT_LOADED);
  });

  // The page is served by another process on loopback. Nothing in it should ever
  // open a new window, and a navigation away from the surface is a bug or worse.
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith(target.url)) {
      event.preventDefault();
    }
  });

  mainWindow.loadURL(target.url);
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

// A second launch focuses the first rather than starting a rival that would fail
// to bind the port and look like a broken application.
if (!app.requestSingleInstanceLock()) {
  app.exit(0);
} else {
  app.on("second-instance", () => {
    if (mainWindow !== null && !mainWindow.isDestroyed()) {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    try {
      target = endpoint.resolve(process.env);
    } catch {
      refuse(ENDPOINT_UNRESOLVED);
      return;
    }

    remembered = readState();

    if (!(await ensureSurface())) {
      return;
    }

    createWindow();
    createTray();
  });

  // Closing every window does NOT quit. That is the whole point of the tray.
  app.on("window-all-closed", () => {});

  app.on("before-quit", () => {
    quitting = true;
  });

  app.on("will-quit", () => {
    if (surfaceChild !== null) {
      surfaceChild.kill();
      surfaceChild = null;
    }
  });
}
