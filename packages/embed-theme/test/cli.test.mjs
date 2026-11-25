// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { contrast, parseHex } from "../lib/contrast.mjs";

const bin = join(dirname(fileURLToPath(import.meta.url)), "..", "bin", "check-theme.mjs");
const run = (...args) => spawnSync("node", [bin, ...args], { encoding: "utf8" });
const tmp = (css) => {
  const f = join(mkdtempSync(join(tmpdir(), "bb-theme-")), "theme.css");
  writeFileSync(f, css);
  return f;
};

test("ohne Argument: Exit 0", () => {
  assert.equal(run().status, 0);
});

test("zu helle Primärfarbe: Exit 1 und Paar in der Ausgabe", () => {
  const r = run(tmp(":root{--theme-primary:#ff9999}"));
  assert.equal(r.status, 1);
  assert.match(r.stdout + r.stderr, /primary auf white: \d\.\d\d:1 \(mindestens 4\.5:1\)/);
});

test("fehlende Datei: Exit 2", () => {
  assert.equal(run("/nonexistent/theme.css").status, 2);
});

test("--strict: nicht lesbarer Wert ergibt Exit 1, sonst 0", () => {
  const f = tmp(":root{--theme-primary:oklch(0.5 0.2 20)}");
  assert.equal(run(f).status, 0);
  assert.equal(run("--strict", f).status, 1);
});

test("--help und -h: Aufruf auf stdout, Exit 0", () => {
  for (const flag of ["--help", "-h"]) {
    const r = run(flag);
    assert.equal(r.status, 0);
    assert.match(r.stdout, /Aufruf: basicbar-check-theme/);
    assert.doesNotMatch(r.stdout + r.stderr, /nicht lesbar|Kontrast ok/);
  }
});

test("unbekannte Option: Aufruf auf stderr, Exit 2", () => {
  const r = run("--strikt", tmp(":root{}"));
  assert.equal(r.status, 2);
  assert.match(r.stderr, /Unbekannte Option: --strikt/);
  assert.match(r.stderr, /Aufruf:/);
});

test("mehr als eine Datei: Aufruf auf stderr, Exit 2", () => {
  const r = run(tmp(":root{}"), tmp(":root{}"));
  assert.equal(r.status, 2);
  assert.match(r.stderr, /Aufruf:/);
});

test("Tippfehler im Schlüssel: Warnung, mit --strict Exit 1", () => {
  const f = tmp(":root{--theme-primay:#000000}");
  const a = run(f);
  assert.equal(a.status, 0);
  assert.match(a.stdout, /Warnung: --theme-primay/);
  const b = run("--strict", f);
  assert.equal(b.status, 1);
  assert.match(b.stdout, /--theme-primay/);
});

test("Anzeige rundet ab: 4,497 erscheint nicht als 4.50", () => {
  // Hilfsrechnung: Primärfarbe knapp unter 4,5:1 auf Weiß suchen.
  let found;
  const h = (n) => n.toString(16).padStart(2, "0");
  for (let r = 0x60; r < 0x90 && !found; r++) {
    for (let g = 0x60; g < 0x90 && !found; g++) {
      const c = `#${h(r)}${h(g)}80`;
      const ratio = contrast(parseHex(c), [255, 255, 255]);
      if (ratio < 4.5 && ratio >= 4.495) found = [c, ratio];
    }
  }
  assert.ok(found, "kein Grauwert mit 4.495 <= Kontrast < 4.5 gefunden");
  const r = run(tmp(`:root{--theme-text:${found[0]};--theme-primary:#ad1034}`));
  assert.equal(r.status, 1);
  assert.match(r.stdout, /text auf white: 4\.49:1/);
  assert.doesNotMatch(r.stdout, /4\.50/);
});
