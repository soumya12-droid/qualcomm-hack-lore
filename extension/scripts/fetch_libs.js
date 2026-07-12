#!/usr/bin/env node
"use strict";

// Downloads the extension's vendored third-party libraries into
// extension/libs/ — pdf.js (PDF text extraction) and Tesseract.js + its
// WASM OCR cores and English trained-data (image/scanned-PDF OCR).
//
// These are unmodified upstream builds, not project code, so they aren't
// committed to git (see extension/libs/ in .gitignore) — a 16MB, ~90,000
// line diff of someone else's minified/compiled output has no business
// living in this repo's history. Run this once before loading the
// extension (`chrome://extensions` -> Load unpacked -> extension/), and
// again any time extension/libs/ is missing or wiped.
//
// Every URL below is pinned to an exact upstream version and verified by
// sha256 after download, so this always reproduces the exact bytes that
// used to be committed here (confirmed byte-for-byte against the
// previously-vendored copies before this script was written) — not just
// "whatever the latest version happens to be".

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const LIBS_DIR = path.join(__dirname, "..", "libs");

const FILES = [
  {
    dest: "pdf.js",
    url: "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/legacy/build/pdf.js",
    sha256: "8c6a4a46bd1d58c32417f3bbd526ed1a221283214018cdef60ad483c35cceb00",
  },
  {
    dest: "pdf.worker.js",
    url: "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/legacy/build/pdf.worker.js",
    sha256: "343e858b9e2e5353e0476ece39272e9c1e79f44f34bf845ca104f4189e7dc24c",
  },
  {
    dest: "tesseract/tesseract.min.js",
    url: "https://cdn.jsdelivr.net/npm/tesseract.js@7.0.0/dist/tesseract.min.js",
    sha256: "000c27d9cd0def655f77b36c72a389c0ab13793aa31cb4d7aab56d09c0afbc7e",
  },
  {
    dest: "tesseract/worker.min.js",
    url: "https://cdn.jsdelivr.net/npm/tesseract.js@7.0.0/dist/worker.min.js",
    sha256: "576b7df7e3393e137e51849357c9adb53fe7ac1bb69bfa06cf3d61520f182c6d",
  },
  {
    dest: "tesseract/core/tesseract-core-lstm.wasm.js",
    url: "https://cdn.jsdelivr.net/npm/tesseract.js-core@7.0.0/tesseract-core-lstm.wasm.js",
    sha256: "eef5f8b2f8e20e150680b20adaec4a60babafee3adbe8a94583c81fee46e8680",
  },
  {
    dest: "tesseract/core/tesseract-core-simd-lstm.wasm.js",
    url: "https://cdn.jsdelivr.net/npm/tesseract.js-core@7.0.0/tesseract-core-simd-lstm.wasm.js",
    sha256: "c58b46a4c796c0b8afccf77591d5b875b6896b45d402bbce8caa6f5362447b38",
  },
  {
    dest: "tesseract/core/tesseract-core-relaxedsimd-lstm.wasm.js",
    url: "https://cdn.jsdelivr.net/npm/tesseract.js-core@7.0.0/tesseract-core-relaxedsimd-lstm.wasm.js",
    sha256: "861a536cf9ef8e63cb644d57bab39c388f37f7d6b6f60024b741c5f6b39a59b3",
  },
  {
    dest: "tesseract/lang/eng.traineddata.gz",
    // Tesseract.js's own default langPath (jsdelivr's @tesseract.js-data/eng
    // package) turned out to be a different, much larger model — this is
    // the "fast" English model actually used here, confirmed by decompressed
    // byte-for-byte match against the file this script replaces.
    url: "https://tessdata.projectnaptha.com/4.0.0_fast/eng.traineddata.gz",
    sha256: "18c1ac52b75e35d44735fb6c2a60acfaf23033524653200738e98f0243edb75b",
  },
];

async function fetchWithVerification({ dest, url, sha256 }) {
  const destPath = path.join(LIBS_DIR, dest);

  if (fs.existsSync(destPath)) {
    const existing = crypto.createHash("sha256").update(fs.readFileSync(destPath)).digest("hex");
    if (existing === sha256) {
      console.log(`already up to date: ${dest}`);
      return;
    }
  }

  console.log(`downloading ${dest} <- ${url}`);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} responded ${response.status} ${response.statusText}`);
  }
  const buffer = Buffer.from(await response.arrayBuffer());

  const actual = crypto.createHash("sha256").update(buffer).digest("hex");
  if (actual !== sha256) {
    throw new Error(
      `sha256 mismatch for ${dest}: expected ${sha256}, got ${actual}. ` +
      `The upstream file may have changed — do not use it without re-verifying.`
    );
  }

  fs.mkdirSync(path.dirname(destPath), { recursive: true });
  fs.writeFileSync(destPath, buffer);
  console.log(`wrote ${dest} (${buffer.length} bytes, sha256 verified)`);
}

async function main() {
  for (const file of FILES) {
    await fetchWithVerification(file);
  }
  console.log("\nAll extension libraries fetched and verified.");
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
