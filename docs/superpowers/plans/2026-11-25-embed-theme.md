# `@basicbar/embed-theme` – Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Ziel:** Ein neues npm-Paket liefert öffentlichen Tool-Seiten ein anpassbares Erscheinungsbild:
- typgeprüfte `--theme-`-Variablen mit Uni-Osnabrück-Voreinstellung;
- Signika;
- Tailwind-Werte für Tailwind 3 und 4;
- ein Kontrast-Prüfskript;
- eine Vorlage für Betreiber.

**Architektur:**
- Das Paket besteht aus reinen Dateien ohne Bundler: `theme.css`, `tailwind.js`, `lib/contrast.mjs`, `bin/check-theme.mjs`, `template/theme.css` und die Schrift.
- Tests laufen mit `node --test`; für die Tailwind-Ausgabe kommen beide Hauptversionen als Dev-Abhängigkeiten dazu.
- Verteilt wird es als Release-Asset, Tag `embed-theme/vX.Y.Z`, nach ADR-0002.

**Stack:** Node 22, `node:test`, Tailwind 3.4 und 4.x (nur für Tests), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-25-embed-theme-design.md` (bindend).

## Global Constraints

- Paketname `@basicbar/embed-theme`, Version `0.1.0`, Lizenz Apache-2.0. Die Schrift steht unter OFL-1.1 mit `fonts/OFL.txt`.
- Keine Laufzeit-Abhängigkeiten. Tailwind ist keine Peer-Abhängigkeit.
- Präfix `--theme-`. Variablen und Uni-Voreinstellungen exakt so:
  - `primary` #ad1034, `primary-hover` #8a0d2a, `on-primary` #ffffff, `accent` #fbb800;
  - `text` #3e3e3f, `muted` #5e5e5e, `surface` #f3f3f3, `border` #d0d0d0;
  - `field-border` #767676, `danger` #c8102e;
  - `radius` 0, `font` `"Signika Variable", system-ui, sans-serif`, `font-weight` 300.
- Kaskadenschicht der Voreinstellung: `@layer basicbar-theme`.
- Kontrastschwellen:
  - 4,5:1 für Text, Nebentext, Primär, Primär-Hover und Fehler, jeweils auf Weiß und auf `surface`;
  - 4,5:1 für on-primary auf primary und auf primary-hover;
  - 4,5:1 für primary auf dem getönten Hintergrund (8 % primary auf Weiß, in sRGB gemischt);
  - 3:1 für field-border und primary auf Weiß.
- Kommando `basicbar-check-theme [--strict] [datei]`. Exit 0 = ok, 1 = Paar unter Schwelle (oder nicht lesbar mit `--strict`), 2 = Datei nicht lesbar.
- SPDX-Header in jeder Quelldatei: `SPDX-License-Identifier: Apache-2.0` und `Copyright 2026 Universität Osnabrück (virtUOS)`. Die woff2 und `OFL.txt` sind ausgenommen.
- Branch `feat/embed-theme`, nie auf main. Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Kein Push, kein PR ohne ausdrückliche Freigabe durch den Auftraggeber.

## Review Focus

1. **Theme-Datei mit `oklch()`- oder `rgb()`-Werten:** Das Prüfskript warnt und überspringt das Paar; mit `--strict` endet es mit 1. Es stürzt nicht ab. → Test in Task 2.
2. **Theme-Datei mit Kommentaren, `!important`, Großbuchstaben-Hex oder `#rgb`:** wird korrekt gelesen. → Test in Task 2.
3. **`bg-theme-primary/10` in Tailwind 3 und 4:** erzeugt gültiges CSS mit `var(--theme-primary)` und Deckkraft. → Test in Task 1.
4. **Jede Variable** ist in `theme.css` registriert (wo typisierbar) und mit Voreinstellung belegt, und sie ist in `template/theme.css` dokumentiert. → Test in Task 3.
5. **`npm pack`** enthält `theme.css`, `tailwind.js`, `lib/`, `bin/`, `template/` und `fonts/` (woff2 und OFL), aber keine Tests. → Prüfung im CI-Job in Task 3.

---

### Task 1: Paketgerüst, `theme.css`, Schrift, `tailwind.js`

**Files:**
- Create: `packages/embed-theme/package.json`, `packages/embed-theme/theme.css`, `packages/embed-theme/tailwind.js`
- Create: `packages/embed-theme/fonts/signika-latin-wght-normal.woff2`, `packages/embed-theme/fonts/OFL.txt`
- Create: `packages/embed-theme/test/tailwind.test.mjs`, `packages/embed-theme/test/fixtures/` (Eingabe-CSS bzw. Konfiguration je Version)

**Interfaces:**
- Produces:
  ```js
  // tailwind.js (ESM)
  export const themeColorsV4: Record<string, string>; // { primary: "var(--theme-primary)", ... } — key per variable except radius/font/font-weight; plus "primary-tint": "var(--theme-primary-tint)"
  export const themeColorsV3: Record<string, string>; // same keys, values with <alpha-value>
  export const themeBorderRadius: { theme: "var(--theme-radius)" };
  export const themeFontFamily: { theme: string[] }; // ["var(--theme-font)"]
  ```
  `theme.css` definiert zusätzlich `--theme-primary-tint: color-mix(in srgb, var(--theme-primary) 8%, #fff)` und `--theme-hover-surface: color-mix(in srgb, var(--theme-primary) 4%, #fff)`.

- [ ] **Step 1: Schrift beschaffen.**
  - `signika-latin-wght-normal.woff2` aus `@fontsource-variable/signika@5.3.0` kopieren: einmal `npm pack @fontsource-variable/signika@5.3.0` im Scratchpad, die Datei aus `files/` übernehmen.
  - `OFL.txt` aus demselben Paket übernehmen und Copyright-Zeile sowie Herkunft prüfen.
- [ ] **Step 2: `package.json`.**
  - `"type": "module"`.
  - `files`: `theme.css`, `tailwind.js`, `lib`, `bin`, `template`, `fonts`, `README.md`.
  - `exports`: `"./theme.css"`, `"./tailwind"` (→ `./tailwind.js`), `"./template/theme.css"`.
  - `"bin": { "basicbar-check-theme": "./bin/check-theme.mjs" }`.
  - `"scripts": { "test": "node --test test/" }`.
  - `devDependencies`: `"tailwindcss3": "npm:tailwindcss@^3.4.17"`, `"tailwindcss4": "npm:tailwindcss@^4.1"`, `"@tailwindcss/node": "^4.1"`, `"postcss": "^8"`. `package-lock.json` erzeugen.
- [ ] **Step 3: Failing test `test/tailwind.test.mjs`.**
  - **Tailwind 3:** über `postcss([tailwindcss3({ content: [{ raw: '<div class="bg-theme-primary/10 bg-theme-primary rounded-theme font-theme">' }], theme: { extend: { colors: { theme: themeColorsV3 }, borderRadius: themeBorderRadius, fontFamily: themeFontFamily } } })])`. Dabei `@tailwind utilities` verarbeiten.
  - **Erwartung Tailwind 3:**
    - Das Ergebnis enthält `var(--theme-primary)`.
    - Für `/10` steht eine Deckkraft von 0.1 im Wert.
    - `border-radius: var(--theme-radius)` und `font-family: var(--theme-font)` sind vorhanden.
  - **Tailwind 4:** mit `@tailwindcss/node` `compile()` aus einem CSS mit `@import "tailwindcss" source(none); @config "./fixtures/v4.config.js";`. Die Konfiguration nutzt `themeColorsV4`. Dann `build(['bg-theme-primary/10','rounded-theme'])`.
  - **Erwartung Tailwind 4:** `var(--theme-primary)` und `color-mix(` für den Modifikator sowie `var(--theme-radius)`.
- [ ] **Step 4:** `cd packages/embed-theme && npm ci && npm test` → FAIL.
- [ ] **Step 5: Implementieren.**
  - `tailwind.js`: V3-Werte als `color-mix(in srgb, var(--theme-x) calc(<alpha-value> * 100%), transparent)`, V4-Werte als `var(--theme-x)`.
  - `theme.css`:
    - `@property` für alle Farbvariablen (`syntax: "<color>"`, `inherits: true`, `initial-value` = Voreinstellung).
    - `@property` für `--theme-radius` (`<length-percentage>`, initial `0px`) und `--theme-font-weight` (`<number>`, initial `300`).
    - `@layer basicbar-theme { :root { …alle Voreinstellungen, tint, hover-surface… } }`.
    - `@font-face { font-family: "Signika Variable"; font-style: normal; font-display: swap; font-weight: 300 700; src: url("./fonts/signika-latin-wght-normal.woff2") format("woff2-variations"); unicode-range: … }` mit der latin-Spanne wie in Fontsource.
- [ ] **Step 6:** `npm test` → PASS.
- [ ] **Step 7: Commit** `feat(embed-theme): Paket mit Theme-Variablen, Signika und Tailwind-Werten`

### Task 2: Kontrast-Prüfskript

**Files:**
- Create: `packages/embed-theme/lib/contrast.mjs`, `packages/embed-theme/bin/check-theme.mjs`
- Create: `packages/embed-theme/test/contrast.test.mjs`, `packages/embed-theme/test/cli.test.mjs`

**Interfaces:**
- Produces:
  ```js
  // lib/contrast.mjs
  export const DEFAULTS: Record<string, string>;            // the Uni values of the color variables, keys without prefix
  export function parseHex(value: string): [number, number, number] | null; // #rgb / #rrggbb, case-insensitive
  export function contrast(a: [number,number,number], b: [number,number,number]): number; // WCAG 2.x ratio
  export function mix(a, b, weightA: number): [number,number,number]; // sRGB mix, used for primary-tint
  export function readThemeVars(css: string): Record<string, string>; // --theme-* declarations, comments stripped, !important removed, last one wins
  export function checkTheme(vars: Record<string, string>, opts?: { strict?: boolean }): { failures: Array<{ pair: string; ratio: number; min: number }>; warnings: string[] };
  ```

- [ ] **Step 1: Failing tests.**
  - `contrast(parseHex("#ad1034"), parseHex("#fff"))` gerundet auf 2 Stellen = 7.24.
  - `#3e3e3f` auf `#fff` = 10.68.
  - `#767676` auf `#fff` = 4.54.
  - `parseHex("#ABC")` gleich `parseHex("#aabbcc")`; `parseHex("oklch(0.5 0.1 20)")` = null.
  - `readThemeVars("/* --theme-primary: #000; */ :root{--theme-primary:#123456 !important;--theme-primary:#ad1034}")` → `{ primary: "#ad1034" }`.
  - `checkTheme({})`: keine Fehler, keine Warnungen (Voreinstellung).
  - `checkTheme({ primary: "#ff9999" })` meldet unter anderem `primary/white` mit `min` 4.5.
  - `checkTheme({ primary: "oklch(0.5 0.2 20)" })`: Warnung, keine Fehler. Mit `strict` ein Fehler.
  - **CLI** (`node bin/check-theme.mjs` per `child_process`):
    - ohne Argument Exit 0;
    - mit einer Temp-Datei mit zu heller Primärfarbe Exit 1, und die Ausgabe nennt das Paar;
    - mit einer nicht vorhandenen Datei Exit 2.
- [ ] **Step 2:** `npm test` → FAIL.
- [ ] **Step 3: Implementieren.**
  - Die Paarliste steht exakt wie in den Global Constraints. `primary-tint` wird mit `mix(primary, white, 0.08)` berechnet.
  - Die CLI ist dünn: Argumente lesen, `checkTheme` aufrufen.
  - Ausgabe: eine Zeile je Fehler, Format `primary auf white: 3.10:1 (mindestens 4.5:1)`, dann Warnungen.
  - Shebang `#!/usr/bin/env node`, Datei ausführbar.
- [ ] **Step 4:** `npm test` → PASS.
- [ ] **Step 5: Commit** `feat(embed-theme): Kontrast-Prüfskript basicbar-check-theme`

### Task 3: Vorlage, README, CHANGELOG, CI, Publish, Dependabot

**Files:**
- Create: `packages/embed-theme/template/theme.css`, `packages/embed-theme/README.md`, `packages/embed-theme/test/files.test.mjs`
- Modify: `CHANGELOG.md`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `CLAUDE.md` (Layout-Liste und Ruleset-Liste)
- Create: `.github/workflows/publish-embed-theme.yml`

- [ ] **Step 1: Failing test `test/files.test.mjs`.**
  - Jede Variable aus `DEFAULTS` plus `radius`, `font` und `font-weight` kommt in `theme.css` als Voreinstellung vor.
  - Jede Farbvariable hat ein `@property`.
  - Jede Variable steht in `template/theme.css` (auskommentiert).
  - `template/theme.css` besteht `checkTheme` mit `strict`, wenn man die Kommentarzeichen entfernt.
- [ ] **Step 2: Implementieren.**
  - `template/theme.css`: ein Kommentarkopf (Sie-Form) zu „was ist das, wo ablegen, nicht in `@layer` packen, keine externen URLs, prüfen mit `npx basicbar-check-theme`“. Danach je Variable eine auskommentierte Zeile mit Uni-Wert, Bedeutung und Kontrastregel.
  - `README.md`, Teil für Tools:
    - Installation per Release-URL;
    - Import von `theme.css` in die öffentlichen Einstiege;
    - Tailwind 3 (`themeColorsV3`) und Tailwind 4 (`themeColorsV4` per `@config`);
    - `<link rel="stylesheet" href="/theme/theme.css">` in den öffentlichen HTML-Einstiegen und die Vorlage nach `public/theme/` kopieren;
    - der Caddy-Baustein: `file`-Matcher mit `root /srv/theme`, sonst `/srv/www`, ein echtes 404 und Cache-Header;
    - Volume am Caddy-Dienst;
    - CI-Aufruf mit `--strict`.
  - `README.md`, Teil für Betreiber (Sie-Form): Variablentabelle, Beispiel eigene Farbe, Beispiel eigene Schrift per `@font-face` mit Datei im Volume, Prüfschritt, Datenschutzhinweis.
  - `CHANGELOG.md`: Eintrag `embed-theme 0.1.0` mit den Einbindungsschritten.
  - **CI:**
    - Job `embed-theme` (Node 22): `cd packages/embed-theme && npm ci && npm test && npm pack --dry-run --json`.
    - Ein Schritt prüft per `node -e`, dass die Paketliste `theme.css`, `tailwind.js`, `lib/contrast.mjs`, `bin/check-theme.mjs`, `template/theme.css`, `fonts/signika-latin-wght-normal.woff2` und `fonts/OFL.txt` enthält und nichts unter `test/`.
    - Den `find` des Jobs `spdx-header` um `-name '*.js' -o -name '*.mjs'` erweitern.
    - Liegen dann bestehende `.js`-Dateien ohne Header vor, etwa `packages/ui/tailwind-preset.js`, bekommen sie den Header im selben Commit.
  - **Publish:** `publish-embed-theme.yml` analog `publish.yml`, Trigger `embed-theme/v*`. Version gegen `packages/embed-theme/package.json` prüfen, `npm pack`, Asset an ein **Draft**-Release hängen.
  - **Dependabot:** npm-Eintrag für `/packages/embed-theme`, `ignore` für `tailwindcss3` und `tailwindcss4` bei `version-update:semver-major`.
  - **CLAUDE.md:** Layout-Zeile für das Paket. In der Liste der Pflicht-Checks steht künftig `embed-theme`, mit dem Hinweis, dass ein Mensch das Ruleset anpassen muss.
- [ ] **Step 3:** `npm test` → PASS. Lokal den SPDX-`find` aus ci.yml ausführen: keine fehlenden Header.
- [ ] **Step 4: Commit** `feat(embed-theme): Vorlage, Anleitung, CI und Publish`

### Task 4: Erprobung mit Tailwind 3 (ticketBAR, Wegwerf)

Nur Controller und Bericht; kein Commit in ticketBAR.

- [ ] **Step 1:**
  - `npm pack` in `packages/embed-theme`.
  - `git -C ~/dev/ticketbar worktree add <scratchpad>/wt-ticketbar-probe HEAD`. Das ist ein sauberer Stand, denn der Haupt-Checkout hat fremde Änderungen.
  - Im Probe-Worktree:
    - `cd frontend && npm install --no-save <tarball>`;
    - in `src/public/public.css` die Datei `@basicbar/embed-theme/theme.css` importieren;
    - in `tailwind.config.js` `colors.theme = themeColorsV3` sowie `themeBorderRadius` und `themeFontFamily` ergänzen;
    - einem Knopf der Embed-Seite `bg-theme-primary text-theme-on-primary rounded-theme` und einem Element `bg-theme-primary/10` geben;
    - `public/theme/theme.css` mit `--theme-primary: #005f87` anlegen und `<link>` in `public.html` setzen.
- [ ] **Step 2:** `npm run build`. Vite-Dev-Server starten und `/embed` im Browser öffnen.
  - Der Knopf hat #005f87 (berechneter Stil); `/10` ist durchscheinend; die Schrift ist Signika (geladen aus dem Bundle, kein externer Abruf).
  - Nach Löschen von `public/theme/theme.css` ist der Knopf #ad1034.
- [ ] **Step 3:**
  - Befund mit Screenshot als Abschnitt „Ergebnis der Erprobung“ unter „Ablauf“ in der Spec nachtragen und committen (`docs: Erprobung mit Tailwind 3`).
  - Worktree entfernen (`git worktree remove`). In ticketBAR bleibt kein Branch und keine Datei zurück.
