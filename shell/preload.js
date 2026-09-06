"use strict";

// The preload script.
//
// DELIBERATELY ALMOST EMPTY, and that is the design rather than an unfinished
// state. The dashboard is served as ordinary HTML over loopback by another
// process; it needs no privileged capability, so none is exposed. Every bridge
// added here is a hole punched through contextIsolation, and the page's content
// includes a player nickname fetched from a third-party API.
//
// The one thing exposed is a version string, so the page can render what it is
// running against without being handed anything it could act with.
//
// IF THIS FILE EVER GROWS A FUNCTION that reaches the filesystem, the network or
// the shell, that is a decision worth an ADR, not a convenience.

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("resincompute", Object.freeze({
  shellVersion: "0.1.0",
}));
