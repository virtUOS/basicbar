// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

// Tailwind-Werte, die auf die --theme-Variablen aus theme.css zeigen.
// Einbindung unter dem Namen `theme` (bg-theme-primary, rounded-theme, font-theme).

const KEYS = [
  "primary",
  "primary-hover",
  "on-primary",
  "accent",
  "text",
  "muted",
  "surface",
  "border",
  "field-border",
  "danger",
  "primary-tint",
];

// Tailwind 4 setzt <alpha-value> im JS-Konfigurationsmodus vorab auf 1 und
// bildet Deckkraft-Modifikatoren selbst mit color-mix: schlichte var()-Werte.
export const themeColorsV4 = Object.fromEntries(
  KEYS.map((k) => [k, `var(--theme-${k})`]),
);

// Tailwind 3 ersetzt <alpha-value> durch die Deckkraft (bg-theme-primary/10).
export const themeColorsV3 = Object.fromEntries(
  KEYS.map((k) => [
    k,
    `color-mix(in srgb, var(--theme-${k}) calc(<alpha-value> * 100%), transparent)`,
  ]),
);

export const themeBorderRadius = { theme: "var(--theme-radius)" };

export const themeFontFamily = { theme: ["var(--theme-font)"] };
