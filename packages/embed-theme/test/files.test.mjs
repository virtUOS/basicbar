// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { DEFAULTS, readThemeVars, checkTheme } from "../lib/contrast.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const read = (f) => readFileSync(join(root, f), "utf8");
const themeCss = read("theme.css");
const template = read("template/theme.css");

const colorNames = Object.keys(DEFAULTS);
const allNames = [...colorNames, "radius", "font", "font-weight"];

test("theme.css: jede Variable hat eine Voreinstellung in @layer basicbar-theme", () => {
  const layer = themeCss.slice(themeCss.indexOf("@layer basicbar-theme"));
  const vars = readThemeVars(layer);
  for (const n of allNames) assert.ok(n in vars, `--theme-${n} fehlt in der Voreinstellung`);
  for (const [n, v] of Object.entries(DEFAULTS)) assert.equal(vars[n], v, `--theme-${n}`);
});

test("theme.css: jede Farbvariable ist per @property registriert", () => {
  for (const n of colorNames) {
    assert.match(themeCss, new RegExp(`@property --theme-${n} \\{[^}]*syntax: "<color>"`), n);
  }
});

test("template/theme.css: jede Variable steht auskommentiert in der Vorlage", () => {
  for (const n of allNames) {
    assert.match(template, new RegExp(`/\\*\\s*--theme-${n}\\s*:`), `--theme-${n} fehlt`);
  }
});

test("template/theme.css: ohne Kommentarzeichen besteht die Vorlage checkTheme strict", () => {
  const active = template.replace(/\/\*\s*(--theme-[^*]*?;)\s*\*\//g, "$1");
  const vars = readThemeVars(active);
  for (const n of allNames) assert.ok(n in vars, `--theme-${n} nicht aktiviert`);
  for (const [n, v] of Object.entries(DEFAULTS)) assert.equal(vars[n], v);
  const { failures, warnings } = checkTheme(vars, { strict: true });
  assert.deepEqual(failures, []);
  assert.deepEqual(warnings, []);
});

test("template/theme.css: keine @media, @layer oder externen URLs", () => {
  const code = template.replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(code, /@media|@layer|https?:/);
});
