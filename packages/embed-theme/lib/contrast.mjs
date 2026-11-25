// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

// Uni-Voreinstellung der Farbvariablen (Schlüssel ohne Präfix --theme-).
// Muss mit theme.css übereinstimmen.
export const DEFAULTS = {
  primary: "#ad1034",
  "primary-hover": "#8a0d2a",
  "on-primary": "#ffffff",
  accent: "#fbb800",
  text: "#3e3e3f",
  muted: "#5e5e5e",
  surface: "#f3f3f3",
  border: "#d0d0d0",
  "field-border": "#767676",
  danger: "#c8102e",
};

const WHITE = [255, 255, 255];

// Weitere erlaubte Schlüssel neben den Farben.
const OTHER_KEYS = ["radius", "font", "font-weight"];
const LENGTH = /^(0|[+]?(\d+\.?\d*|\.\d+)(px|rem|em|%|ch|ex|cm|mm|in|pt|pc|vw|vh|vmin|vmax))$/i;

function syntaxProblem(name, value) {
  if (name === "radius" && !LENGTH.test(value)) {
    return `--theme-radius: "${value}" ist keine Länge (etwa 0, 6px, 0.5rem) oder Prozentangabe`;
  }
  if (name === "font-weight") {
    const n = Number(value);
    if (!/^[+]?(\d+\.?\d*|\.\d+)$/.test(value) || !(n >= 1 && n <= 1000)) {
      return `--theme-font-weight: "${value}" ist keine Zahl zwischen 1 und 1000`;
    }
  }
  return null;
}

export function parseHex(value) {
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(value).trim());
  if (!m) return null;
  let h = m[1];
  if (h.length === 3) h = [...h].map((c) => c + c).join("");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
}

function luminance([r, g, b]) {
  const lin = (c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

export function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

export function mix(a, b, weightA) {
  return a.map((c, i) => c * weightA + b[i] * (1 - weightA));
}

export function readThemeVars(css) {
  const out = {};
  const clean = css.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const m of clean.matchAll(/--theme-([a-z0-9-]+)\s*:\s*([^;}]+)/gi)) {
    out[m[1]] = m[2].replace(/!important\s*$/i, "").trim();
  }
  return out;
}

// [Vordergrund, Hintergrund, Mindestkontrast]
const PAIRS = [
  ...["text", "muted", "primary", "primary-hover", "danger"].flatMap((fg) => [
    [fg, "white", 4.5],
    [fg, "surface", 4.5],
  ]),
  ["on-primary", "primary", 4.5],
  ["on-primary", "primary-hover", 4.5],
  ["primary", "primary-tint", 4.5],
  ["field-border", "white", 3],
  // primary auf Weiß (3:1) ist durch die 4,5:1-Prüfung oben abgedeckt.
];

export function checkTheme(vars, opts = {}) {
  const merged = { ...DEFAULTS, ...vars };
  const failures = [];
  const warnings = [];
  const colors = { white: WHITE };
  const unreadable = new Set();
  const report = (msg, pair) => {
    if (opts.strict) failures.push({ pair, ratio: 0, min: 0, reason: msg });
    else warnings.push(msg);
  };

  const known = new Set([...Object.keys(DEFAULTS), ...OTHER_KEYS]);
  for (const name of Object.keys(vars)) {
    if (!known.has(name)) {
      report(`--theme-${name} ist unbekannt (Tippfehler?) und wird ignoriert`, `${name} (unbekannt)`);
    }
  }
  for (const name of OTHER_KEYS) {
    if (name in vars) {
      const msg = syntaxProblem(name, String(vars[name]).trim());
      if (msg) report(msg, `${name} (ungültig)`);
    }
  }

  for (const name of Object.keys(DEFAULTS)) {
    const rgb = parseHex(merged[name]);
    if (rgb) colors[name] = rgb;
    else {
      unreadable.add(name);
      const msg = `--theme-${name}: "${merged[name]}" ist kein Hex-Wert, Kontrast nicht prüfbar`;
      if (opts.strict) failures.push({ pair: `${name} (nicht lesbar)`, ratio: 0, min: 0, reason: msg });
      else warnings.push(msg);
    }
  }
  if (colors.primary) colors["primary-tint"] = mix(colors.primary, WHITE, 0.08);

  for (const [fg, bg, min] of PAIRS) {
    if (!colors[fg] || !colors[bg]) continue;
    const ratio = contrast(colors[fg], colors[bg]);
    if (ratio < min) failures.push({ pair: `${fg}/${bg}`, ratio, min });
  }
  return { failures, warnings };
}
