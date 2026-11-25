// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

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
