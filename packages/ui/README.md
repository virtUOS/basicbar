# @basicbar/ui

Design-System-Basis der „-bar“-Tools: **ein System, pro Tool ein eigener
Akzent.** Das Paket teilt Struktur und Verhalten — Font, Dark Mode,
Motion-Tokens, A11y-Basis, i18n-Bootstrap —, während die Farb-Ramps als
Identität im Tool bleiben (ausleihbar Honig, abstimmbar Grün). Wollen zwei
Tools identisch aussehen, übergeben sie dieselbe Ramp.

## Bausteine

- **`@basicbar/ui/tailwind-preset`** — `createPreset({ colors })`: Font-Stack
  (Plus Jakarta Sans Variable), Dark Mode per `.dark`-Klasse, Motion-Tokens
  (`pop`, `fade-up`, `out-quart`). Die `slate`/`brand`-Ramps übergibt das Tool
  (OKLCH, Konventionen im Preset-Docstring).
- **`@basicbar/ui/base.css`** — gemeinsamer `@layer base`: Canvas hell/dunkel,
  `accent-color`, `::selection`, konsistenter `:focus-visible`-Ring
  (WCAG 2.4.7), `color-scheme`-Regeln, Skip-Link (WCAG 2.4.1),
  `prefers-reduced-motion`, `text-wrap: balance`, tabellarische Ziffern.
  Als erste Zeile der Tool-`index.css` importieren.
- **`ThemeProvider` / `useTheme` / `prePaintScript`** — Auto/Light/Dark mit
  Live-Systemfolge und `color-scheme`-Sync; `storageKey` konfigurierbar
  (Bestands-Deployments behalten gespeicherte Wahl). `prePaintScript()`
  liefert das Inline-Skript für `index.html` gegen den Theme-Flash.
- **`initI18n({ resources, languages? })`** — i18next-Setup (Englisch als
  Key, Plural-Sonderfall, localStorage+Navigator-Detection,
  `<html lang>`-Sync nach WCAG 3.1.1). Die Kataloge bleiben im Tool.
- **`contentLang`** — `localizedText`/`localizedMap`/`setLocalizedLang` & Co.
  für `{ lang: text }`-Inhalte (Spiegel des Backend-`resolve_translated_text`).

## Einbinden

```ts
// tailwind.config.js
import { createPreset } from "@basicbar/ui/tailwind-preset";
export default {
  presets: [createPreset({ colors: { slate: {/* Tool-Ramp */}, brand: {/* Tool-Ramp */} } })],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
};

// index.css
@import "@basicbar/ui/base.css";
@tailwind base; @tailwind components; @tailwind utilities;

// main.tsx
import { initI18n, ThemeProvider } from "@basicbar/ui";
initI18n({ resources: { en, de } });
```

Build: `npm install && npm run build` (tsup → `dist/`). Distribution als
npm-Tarball über ein GitHub-Release-Asset (siehe ADR-0002, ADR-0004 und
Repo-CI).
