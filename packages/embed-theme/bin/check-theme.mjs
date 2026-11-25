#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import { readFileSync } from "node:fs";
import { checkTheme, readThemeVars } from "../lib/contrast.mjs";

const USAGE = "Aufruf: basicbar-check-theme [--strict] [datei]";
const args = process.argv.slice(2);
if (args.includes("--help") || args.includes("-h")) {
  console.log(USAGE);
  process.exit(0);
}
const unknown = args.filter((a) => a.startsWith("-") && a !== "--strict");
const files = args.filter((a) => !a.startsWith("-"));
if (unknown.length || files.length > 1) {
  console.error(unknown.length ? `Unbekannte Option: ${unknown.join(" ")}` : "Nur eine Datei erlaubt.");
  console.error(USAGE);
  process.exit(2);
}
const strict = args.includes("--strict");
const file = files[0];

// Anzeige abgerundet, damit 4,497 nie als 4,50 erscheint.
const show = (r) => (Math.floor(r * 100) / 100).toFixed(2);

let css = "";
if (file) {
  try {
    css = readFileSync(file, "utf8");
  } catch (e) {
    console.error(`Datei nicht lesbar: ${file} (${e.code ?? e.message})`);
    process.exit(2);
  }
}
const vars = readThemeVars(css);

const { failures, warnings } = checkTheme(vars, { strict });
for (const f of failures) {
  if (f.reason) console.log(f.reason);
  else console.log(`${f.pair.replace("/", " auf ")}: ${show(f.ratio)}:1 (mindestens ${f.min}:1)`);
}
for (const w of warnings) console.log(`Warnung: ${w}`);
if (!failures.length) console.log("Kontrast ok.");
process.exit(failures.length ? 1 : 0);
