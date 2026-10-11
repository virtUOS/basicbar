// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/**
 * Shared Tailwind preset of the -bar tools: one design system, per-tool accent.
 *
 * The preset carries everything that is identical across tools — font stack,
 * class-based dark mode, motion tokens — while the color ramps stay in the
 * tool: they ARE the tool's identity (ausleihbar honey, abstimmbar green).
 *
 * Ramp conventions (keep these when authoring a tool ramp, see the READMEs of
 * the existing tools; values are OKLCH and tuned for WCAG AA):
 * - `slate` is the neutral ramp, usually hue-tinted toward the accent
 *   (warm for honey, cool for green). Muted text (typically slate-400/500)
 *   must reach ≥4.5:1 on the page and card backgrounds in BOTH themes — a
 *   single ramp value often can't, so check light and dark and, if needed,
 *   drive it through a CSS variable that dark mode lifts.
 * - Form-control borders and error text are NOT ramp steps: use the `field`
 *   and `danger` tokens below (variables `--bb-field-border` / `--bb-danger`
 *   with contrast-checked defaults in base.css; tools override the variables
 *   to tint them).
 * - `brand` is the single accent: CTAs use brand-400 with dark ink text,
 *   brand-600 is the focus/selection color (≥3:1 non-text on white),
 *   brand-700 is accent text on white (≥4.5:1).
 * - Append `/ <alpha-value>` to every value so Tailwind's opacity modifier
 *   (e.g. `bg-slate-900/90`) works; without it those utilities render
 *   transparent.
 *
 * Usage in a tool's tailwind.config.js:
 *
 *   import { createPreset } from "@basicbar/ui/tailwind-preset";
 *   export default {
 *     presets: [createPreset({ colors: { slate: {...}, brand: {...} } })],
 *     content: ["./index.html", "./src/**\/*.{js,ts,jsx,tsx}"],
 *   };
 */

/**
 * @param {{ colors: { slate: Record<string, string>, brand: Record<string, string> } }} options
 * @returns {import('tailwindcss').Config}
 */
export function createPreset({ colors } = {}) {
  if (!colors?.slate || !colors?.brand) {
    throw new Error(
      "@basicbar/ui: createPreset braucht die Tool-Farbrampen — createPreset({ colors: { slate, brand } })."
    );
  }
  return {
    // Dark mode is opt-in via a `.dark` class on <html> (toggled by the theme
    // provider from the Auto/Light/Dark setting), not the `media` strategy, so
    // a manual choice can override the system preference.
    darkMode: "class",
    theme: {
      extend: {
        fontFamily: {
          sans: [
            '"Plus Jakarta Sans Variable"',
            "system-ui",
            "-apple-system",
            '"Segoe UI"',
            "Roboto",
            "sans-serif",
          ],
        },
        colors: {
          // Semantic tokens; defaults live in base.css. Tools tint them by
          // overriding the CSS variables, not by redefining `field`/`danger`.
          field: "oklch(var(--bb-field-border) / <alpha-value>)",
          danger: "oklch(var(--bb-danger) / <alpha-value>)",
          ...colors,
        },
        transitionTimingFunction: {
          "out-quart": "cubic-bezier(0.25, 1, 0.5, 1)",
        },
        keyframes: {
          pop: {
            "0%": { transform: "scale(0.6)" },
            "70%": { transform: "scale(1.12)" },
            "100%": { transform: "scale(1)" },
          },
          "fade-up": {
            "0%": { opacity: "0", transform: "translateY(4px)" },
            "100%": { opacity: "1", transform: "translateY(0)" },
          },
        },
        animation: {
          pop: "pop 0.25s cubic-bezier(0.25, 1, 0.5, 1)",
          "fade-up": "fade-up 0.2s cubic-bezier(0.25, 1, 0.5, 1)",
        },
      },
    },
  };
}
