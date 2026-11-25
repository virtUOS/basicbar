#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import { readFileSync } from "node:fs";
import { checkTheme, readThemeVars } from "../lib/contrast.mjs";

const args = process.argv.slice(2);
const strict = args.includes("--strict");
const file = args.find((a) => !a.startsWith("--"));

let vars = {};
if (file) {
  try {
    vars = readThemeVars(readFileSync(file, "utf8"));
  } catch (e) {
    console.error(`Datei nicht lesbar: ${file} (${e.code ?? e.message})`);
    process.exit(2);
  }
}

const { failures, warnings } = checkTheme(vars, { strict });
for (const f of failures) {
  if (f.reason) console.log(f.reason);
  else console.log(`${f.pair.replace("/", " auf ")}: ${f.ratio.toFixed(2)}:1 (mindestens ${f.min}:1)`);
}
for (const w of warnings) console.log(`Warnung: ${w}`);
if (!failures.length) console.log("Kontrast ok.");
process.exit(failures.length ? 1 : 0);
