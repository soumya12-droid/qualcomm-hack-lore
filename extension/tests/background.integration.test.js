"use strict";

// Integration test: loads the real background.js in a vm sandbox with the
// REAL global fetch (no stub) pointed at PC_ENDPOINT, and checks that a
// captured page actually round-trips through a live pc/api backend — i.e.
// that background.js's request body still matches what
// pc/api/routes_index.py's IndexRequest schema expects, and that the
// content becomes searchable via POST /query afterwards.
//
// Requires a real backend already running at http://localhost:8000 (see
// SNAPDRAGON_PC_SETUP.md — `uvicorn pc.api.main:app --host 0.0.0.0 --port
// 8000`). Skips with a clear message rather than failing if it's not
// reachable, since this isn't meant to run unattended in the Python-only
// CI path.

const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const PC_ENDPOINT = "http://localhost:8000";

function loadBackgroundScript() {
  const capturedListeners = [];
  const sandbox = {
    console,
    importScripts: () => {},
    chrome: {
      runtime: {
        onMessage: {
          addListener: (fn) => capturedListeners.push(fn),
        },
      },
    },
    fetch, // real, global Node fetch — no mock
  };
  vm.createContext(sandbox);

  const source = fs.readFileSync(path.join(__dirname, "..", "background.js"), "utf8");
  vm.runInContext(source, sandbox, { filename: "background.js" });

  assert.equal(capturedListeners.length, 1);
  return capturedListeners[0];
}

async function backendIsReachable() {
  try {
    const res = await fetch(`${PC_ENDPOINT}/health`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

test("a captured page really reaches a live PC backend and becomes searchable", async (t) => {
  if (!(await backendIsReachable())) {
    t.skip(`No backend reachable at ${PC_ENDPOINT} — start uvicorn first (see SNAPDRAGON_PC_SETUP.md).`);
    return;
  }

  const onMessage = loadBackgroundScript();
  const marker = `lore-extension-integration-test-${Date.now()}`;
  const url = `https://example.com/${marker}`;

  onMessage({
    type: "CAPTURE_PAGE",
    data: {
      url,
      title: "Extension Integration Test Page",
      content: `This page exists only to prove the browser extension can reach the real backend. Marker: ${marker}`,
    },
  });

  // sendToLore() isn't awaited by the onMessage listener (fire-and-forget,
  // same as in production) — poll briefly for the row to land instead of
  // guessing a fixed delay.
  const deadline = Date.now() + 5000;
  let found = false;
  while (Date.now() < deadline && !found) {
    const res = await fetch(`${PC_ENDPOINT}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: marker, modality: "text" }),
    });
    const body = await res.json();
    found = (body.sources || []).some((s) => s.location === url);
    if (!found) await new Promise((resolve) => setTimeout(resolve, 300));
  }

  assert.ok(found, "content captured by background.js should be searchable via the real /query endpoint");
});
