// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import test from "node:test";
import assert from "node:assert/strict";
import { DEFAULTS, parseHex, contrast, mix, readThemeVars, checkTheme } from "../lib/contrast.mjs";

const r2 = (n) => Math.round(n * 100) / 100;

test("contrast: bekannte Werte", () => {
  assert.equal(r2(contrast(parseHex("#ad1034"), parseHex("#fff"))), 7.24);
  assert.equal(r2(contrast(parseHex("#3e3e3f"), parseHex("#fff"))), 10.68);
  assert.equal(r2(contrast(parseHex("#767676"), parseHex("#fff"))), 4.54);
});

test("parseHex", () => {
  assert.deepEqual(parseHex("#ABC"), parseHex("#aabbcc"));
  assert.deepEqual(parseHex("#aabbcc"), [170, 187, 204]);
  assert.equal(parseHex("oklch(0.5 0.1 20)"), null);
  assert.equal(parseHex("#abcd"), null);
});

test("mix", () => {
  assert.deepEqual(mix([0, 0, 0], [255, 255, 255], 0.5), [127.5, 127.5, 127.5]);
});

test("readThemeVars: Kommentare, !important, letzter gewinnt", () => {
  assert.deepEqual(
    readThemeVars("/* --theme-primary: #000; */ :root{--theme-primary:#123456 !important;--theme-primary:#ad1034}"),
    { primary: "#ad1034" },
  );
});

test("DEFAULTS enthält die Uni-Farben", () => {
  assert.equal(DEFAULTS.primary, "#ad1034");
  assert.equal(DEFAULTS["field-border"], "#767676");
});

test("checkTheme: Voreinstellung ist sauber", () => {
  assert.deepEqual(checkTheme({}), { failures: [], warnings: [] });
  assert.deepEqual(checkTheme({}, { strict: true }), { failures: [], warnings: [] });
});

test("checkTheme: zu helles primary", () => {
  const { failures } = checkTheme({ primary: "#ff9999" });
  const f = failures.find((x) => x.pair === "primary/white");
  assert.ok(f);
  assert.equal(f.min, 4.5);
  assert.ok(f.ratio < 4.5);
});

test("checkTheme: Nicht-Hex ist Warnung, mit strict Fehler", () => {
  const a = checkTheme({ primary: "oklch(0.5 0.2 20)" });
  assert.equal(a.failures.length, 0);
  assert.equal(a.warnings.length, 1);
  assert.match(a.warnings[0], /primary/);
  const b = checkTheme({ primary: "oklch(0.5 0.2 20)" }, { strict: true });
  assert.ok(b.failures.length >= 1);
});

test("checkTheme: field-border braucht 3:1", () => {
  const { failures } = checkTheme({ "field-border": "#cccccc" });
  assert.ok(failures.some((x) => x.pair === "field-border/white" && x.min === 3));
});
