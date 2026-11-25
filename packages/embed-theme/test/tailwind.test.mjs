// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import postcss from "postcss";
import tailwindcss3 from "tailwindcss3";
import { compile } from "@tailwindcss/node";
import {
  themeColorsV3,
  themeColorsV4,
  themeBorderRadius,
  themeFontFamily,
} from "../tailwind.js";

const here = dirname(fileURLToPath(import.meta.url));

test("Tailwind 3: Farbe, Deckkraft-Modifikator, Radius, Schrift", async () => {
  const result = await postcss([
    tailwindcss3({
      content: [
        {
          raw: '<div class="bg-theme-primary/10 bg-theme-primary rounded-theme font-theme">',
        },
      ],
      theme: {
        extend: {
          colors: { theme: themeColorsV3 },
          borderRadius: themeBorderRadius,
          fontFamily: themeFontFamily,
        },
      },
    }),
  ]).process("@tailwind utilities;", { from: undefined });
  const css = result.css;
  assert.match(css, /var\(--theme-primary\)/);
  assert.match(css, /calc\(0\.1 \* 100%\)/);
  assert.match(css, /border-radius:\s*var\(--theme-radius\)/);
  assert.match(css, /font-family:\s*var\(--theme-font\)/);
});

test("Tailwind 4: Farbe, color-mix-Modifikator, Radius", async () => {
  const input = readFileSync(join(here, "fixtures/v4.css"), "utf8");
  const compiler = await compile(input, {
    base: join(here, "fixtures"),
    onDependency: () => {},
  });
  const css = compiler.build(["bg-theme-primary/10", "rounded-theme"]);
  assert.match(css, /var\(--theme-primary\)/);
  assert.match(css, /color-mix\(/);
  assert.match(css, /var\(--theme-radius\)/);
});

test("Farbwerte: gleiche Schlüssel in V3 und V4, inkl. primary-tint", () => {
  assert.deepEqual(Object.keys(themeColorsV3), Object.keys(themeColorsV4));
  assert.equal(themeColorsV4["primary-tint"], "var(--theme-primary-tint)");
  assert.equal(themeColorsV4.primary, "var(--theme-primary)");
  assert.equal(themeBorderRadius.theme, "var(--theme-radius)");
  assert.deepEqual(themeFontFamily.theme, ["var(--theme-font)"]);
});

test("Farbwerte: hover-surface ist enthalten (V3 und V4)", () => {
  assert.equal(themeColorsV4["hover-surface"], "var(--theme-hover-surface)");
  assert.match(themeColorsV3["hover-surface"], /var\(--theme-hover-surface\)/);
});
