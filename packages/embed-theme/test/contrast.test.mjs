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

const pairs = (vars) => checkTheme(vars).failures.map((f) => f.pair);

test("checkTheme: on-primary auf primary", () => {
  assert.ok(pairs({ primary: "#ff9999" }).includes("on-primary/primary"));
});

test("checkTheme: on-primary auf primary-hover", () => {
  const p = pairs({ "primary-hover": "#ff9999" });
  assert.ok(p.includes("on-primary/primary-hover"));
  assert.ok(!p.includes("on-primary/primary"));
});

test("checkTheme: primary-hover auf white und auf surface", () => {
  const p = pairs({ "primary-hover": "#ff9999" });
  assert.ok(p.includes("primary-hover/white"));
  assert.ok(p.includes("primary-hover/surface"));
});

test("checkTheme: surface-Hintergrund ist entscheidend", () => {
  // #767676 hat auf Weiß 4,54:1, auf #f3f3f3 weniger als 4,5:1.
  const p = pairs({ muted: "#767676" });
  assert.ok(p.includes("muted/surface"));
  assert.ok(!p.includes("muted/white"));
  assert.ok(pairs({ text: "#767676" }).includes("text/surface"));
  assert.ok(pairs({ danger: "#767676" }).includes("danger/surface"));
  assert.ok(pairs({ primary: "#767676" }).includes("primary/surface"));
});

test("checkTheme: primary-tint (8 % primary auf Weiß) ist entscheidend", () => {
  // #0067f0 besteht 4,5:1 auf Weiß und surface, aber nicht auf dem Tint.
  assert.deepEqual(pairs({ primary: "#0067f0" }), ["primary/primary-tint"]);
});

test("checkTheme: unbekannter Schlüssel (Tippfehler) warnt, mit strict Fehler", () => {
  const a = checkTheme({ primay: "#000000" });
  assert.equal(a.failures.length, 0);
  assert.equal(a.warnings.length, 1);
  assert.match(a.warnings[0], /--theme-primay/);
  const b = checkTheme({ primay: "#000000" }, { strict: true });
  assert.equal(b.failures.length, 1);
  assert.match(b.failures[0].reason, /--theme-primay/);
});

test("checkTheme: radius muss Länge, Prozent oder 0 sein", () => {
  for (const ok of ["0", "0px", "6px", "0.5rem", ".5em", "50%"]) {
    assert.deepEqual(checkTheme({ radius: ok }, { strict: true }), { failures: [], warnings: [] }, ok);
  }
  for (const bad of ["round", "6", "px", "6 px", "-1px", "calc(1px"]) {
    assert.equal(checkTheme({ radius: bad }).warnings.length, 1, bad);
    assert.equal(checkTheme({ radius: bad }, { strict: true }).failures.length, 1, bad);
  }
});

test("checkTheme: font-weight muss Zahl 1 bis 1000 sein", () => {
  for (const ok of ["1", "300", "450.5", "1000"]) {
    assert.deepEqual(checkTheme({ "font-weight": ok }, { strict: true }), { failures: [], warnings: [] }, ok);
  }
  for (const bad of ["bold", "0", "1001", "-5", "3 00", ""]) {
    assert.equal(checkTheme({ "font-weight": bad }).warnings.length, 1, bad);
    assert.equal(checkTheme({ "font-weight": bad }, { strict: true }).failures.length, 1, bad);
  }
});

test("checkTheme: font und font-weight/radius-Defaults sind bekannte Schlüssel", () => {
  assert.deepEqual(
    checkTheme({ font: "Arial, sans-serif", radius: "4px", "font-weight": "400" }, { strict: true }),
    { failures: [], warnings: [] },
  );
});
