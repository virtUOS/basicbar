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
- **`@basicbar/ui/base.css`** — gemeinsame Basis-Styles (`@layer base` plus
  ungelayerte ProseMirror-Regeln): Canvas hell/dunkel,
  `accent-color`, `::selection`, konsistenter `:focus-visible`-Ring
  (WCAG 2.4.7), `color-scheme`-Regeln, Skip-Link (WCAG 2.4.1),
  `prefers-reduced-motion`, `text-wrap: balance`, tabellarische Ziffern,
  dazu die ProseMirror-Grundregeln für `RichTextEditor` (siehe „CSP“).
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
- **`TranslatableField` / `TranslationFormProvider` / `TranslationControlsSlot`**
  — Sprach-Tabs pro Feld plus verschiebbare Leiste „alle Felder übersetzen“,
  optional im Formular angedockt (siehe `TranslatableField.tsx`).
- **`RichText` / `stripHtml` / `isEmptyHtml`** — Rendern und Prüfen des
  gespeicherten Rich-HTML; **`RichTextEditor`** (TipTap) als **eigener Entry**
  `@basicbar/ui/rich-text-editor`, damit TipTap/ProseMirror nur in Bundles
  landet, die den Editor wirklich rendern (siehe „Rich text“).

## Einbinden

```ts
// tailwind.config.js
import { createPreset } from "@basicbar/ui/tailwind-preset";
export default {
  presets: [createPreset({ colors: { slate: {/* Tool-Ramp */}, brand: {/* Tool-Ramp */} } })],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/@basicbar/ui/dist/**/*.js",
  ],
};

// index.css
@import "@basicbar/ui/base.css";
@tailwind base; @tailwind components; @tailwind utilities;

// main.tsx
import { initI18n, ThemeProvider } from "@basicbar/ui";
initI18n({ resources: { en, de } });
```

Der `dist`-Glob ist nötig, weil die Komponenten des Pakets (z. B.
`RichTextEditor`, `PreferencesMenu`) ihre Tailwind-Klassen im Paket-Code
tragen — ohne den Glob erzeugt Tailwind dafür kein CSS.

Build: `npm install && npm run build` (tsup → `dist/`). Distribution als
npm-Tarball über ein GitHub-Release-Asset (siehe ADR-0002, ADR-0004 und
Repo-CI).

## Rich text

`RichTextEditor` (TipTap) + `RichText` — der eine WYSIWYG-Editor für
formatierte Langtext-Felder (Fett, Kursiv, Aufzählungen, nummerierte Listen,
Link, Überschriften H2/H3, optional Bilder) und die passende Renderkomponente
für das gespeicherte HTML. Aus AbstimmBAR in die Basis verschoben
(modulierbar#5), damit alle -bar-Tools eine Implementierung teilen.

**Import-Pfade:** der Editor kommt aus dem eigenen Entry
`@basicbar/ui/rich-text-editor`; `RichText`, `stripHtml` und `isEmptyHtml`
aus `@basicbar/ui`. Grund: TipTap + ProseMirror sind ~300 kB (≈95 kB gzip)
und sollen nur in Bundles landen, die den Editor rendern — ein Tool, das nur
`RichText` anzeigt oder gar kein Rich-Text hat, zahlt sonst mit. Wer den
Editor nur auf Admin-Seiten braucht, lädt ihn zusätzlich per `React.lazy`
nach, dann liegt er in einem eigenen Chunk.

```tsx
import { RichText, stripHtml, isEmptyHtml } from "@basicbar/ui";
import { RichTextEditor } from "@basicbar/ui/rich-text-editor";
```

**Sanitizing-Vertrag:** die Komponenten selbst sanitizen nichts — die
Sicherheitsgrenze ist das Backend. Jedes Rich-Text-Feld muss beim Speichern
(und beim Import) durch einen Allowlist-Sanitizer laufen, z. B.
`basicbar_integrations.html_sanitize.clean_html`, der auf genau das Subset
reduziert, das der Editor erzeugt (`p`, `strong`, `em`, `h2`, `h3`, `ul`,
`ol`, `li`, `a[href,rel]`, `img[src]`, …). Bild-URLs müssen relativ sein
(`/media/…`) — der Editor fügt nur ein, was `onUploadImage` zurückgibt, ohne
es zu validieren. Der Editor selbst bietet bewusst **nur** dieses Subset an:
Unterstreichen/Durchgestrichen sind nicht registriert (TipTap-`underline`/
`strike` explizit aus) und Links tragen kein `target`/`rel` (das Backend
erzwingt `rel="noopener"` ohnehin) — eine Formatierung, die der Sanitizer
später wieder entfernt, soll der Nutzer erst gar nicht setzen können.

**Zugänglicher Name:** der Editor braucht immer entweder `ariaLabel` (kein
sichtbares Label) oder `labelledBy` (Id eines bereits vorhandenen sichtbaren
`<label>`-Elements, z. B. `TranslatableField`s `labelId` — siehe unten).

**Editor ohne Bilder** (kein Upload-Endpunkt verdrahtet — kein Bild-Button,
Drag&Drop/Einfügen aus der Zwischenablage werden ignoriert; bestehende
`<img>`-Inhalte bleiben trotzdem sichtbar):

```tsx
import { RichTextEditor } from "@basicbar/ui/rich-text-editor";

<RichTextEditor
  value={description}
  onChange={setDescription}
  ariaLabel={t("Description")}
/>
```

**Schreibgeschützt** mit `editable={false}`: kein Toolbar, kein Cursor,
Dateien per Drop/Paste werden ignoriert — z. B. während ein Formular
speichert oder für Nutzer ohne Schreibrecht. Für die reine Anzeige
gespeicherten HTMLs ist `RichText` das richtige Werkzeug (kostet kein TipTap).

**Editor mit Bildern** — `onUploadImage` lädt hoch und liefert die relative
URL als String; scheitert der Upload, zeigt der Editor
`t("Image upload failed")` (plus die Fehlermeldung, falls vorhanden) per
`window.alert` und lässt den Inhalt unverändert:

```tsx
<RichTextEditor
  value={description}
  onChange={setDescription}
  onUploadImage={async (file) => {
    // Eigener Upload-Endpunkt der App; liefert z. B. {"url": "/media/rich/x.png"}.
    const { url } = await postImage(file);
    return url; // relative URL als String
  }}
  id="description-editor"
  ariaLabel={t("Description")}
/>
```

**Bildbeschreibung (Alt-Text, WCAG 1.1.1):** direkt nach einem erfolgreichen
Upload fragt der Editor per `window.prompt` nach einer Beschreibung
(`t("Image description (alt text)")`) — leere Eingabe oder Abbrechen setzen
beide `alt=""` (bewusst dekoratives Bild), das Bild wird in jedem Fall
eingefügt. Ein eigener Toolbar-Button (`t("Image description")`, nur
sichtbar, wenn `onUploadImage` gesetzt ist) ist deaktiviert, solange kein
Bild markiert ist; bei markiertem Bild öffnet er denselben Prompt,
vorausgefüllt mit dem aktuellen Alt-Text, und übernimmt die Änderung —
Abbrechen lässt den bestehenden Alt-Text unangetastet.

**Bilder aus eingefügtem HTML werden gefiltert, nicht nur Datei-Paste/-Drop:**
Fügt man Rich-HTML aus einer Webseite ein (Browser-Copy&Paste, nicht als
Datei), landet es über ProseMirrors HTML-Parser im Dokument — ein
`<img src="https://…">` würde sonst am `onUploadImage`-Flow vorbei direkt
eingefügt und wäre nach dem Speichern ein kaputtes `<img>` (der Backend-
Sanitizer erlaubt nur `/media/…`-Quellen). Der Editor filtert deshalb per
`transformPastedHTML` jedes eingefügte `<img>`, dessen `src` nicht mit
`/media/` beginnt; ohne `onUploadImage` wird jedes eingefügte `<img>`
entfernt (Bilder sind dann vollständig deaktiviert). Das betrifft nur
eingefügtes HTML — vorhandene Bilder im initialen `value` bleiben
unangetastet.

**Rendern** des serverseitig sanitisierten HTML:

```tsx
import { RichText, richTextClass } from "@basicbar/ui";

<RichText html={product.description} />
// eigene Klassen statt des Prosa-Defaults (ersetzt, nicht ergänzt):
<RichText html={product.description} className="text-3xl [&_img]:max-h-64" />
// Prosa-Default ergänzen statt kopieren:
<RichText html={product.description} className={`${richTextClass} mt-4`} />
```

**Prüfen** des gespeicherten HTML — `stripHtml(html)` liefert den sichtbaren
Text (für Listen, Suchtreffer, Platzhalter „kein Fragetext“), `isEmptyHtml(html)`
ist `true` für leere Werte und das `<p></p>`, das ein geöffneter Editor
hinterlässt, aber `false` für reine Bild-Inhalte. Beide parsen per DOM (keine
Regex), ohne etwas auszuführen. `TranslatableField` mit `format="html"`
benutzt `isEmptyHtml` für seine Ausgefüllt-Punkte.

**Integration in `TranslatableField`** über `renderInput` (pro Sprache ein
Editor, mit `format="html"` bleiben die Ausgefüllt-Punkte markup-blind und
die Maschinenübersetzung erhält die Tags). `renderInput` bekommt neben `id`
auch `labelId` — die Id von `TranslatableField`s eigenem sichtbaren `<label>`
(nur gesetzt, wenn die `label`-Prop übergeben wurde); durchgereicht als
`labelledBy` bindet der Editor sich per `aria-labelledby` an dieses Label,
statt ein zweites, redundantes `ariaLabel` zu brauchen. Ebenso `describedBy`
(die Ids der gerade sichtbaren Hilfe-/Statustexte: `hint`, Veraltet-Hinweis,
Pflichtfeld-Fehler) — als `describedBy` durchgereicht setzt der Editor
`aria-describedby`, Screenreader lesen den Hinweis mit dem Feld vor. Auch `onBlur` wird
durchgereicht (die `onBlur`-Prop des Feldes), falls der eigene Editor ein
Blur-Speichern verdrahten will:

```tsx
<TranslatableField
  label={t("Description")}
  values={{ de: form.description_de, en: form.description_en }}
  onChange={(lang, html) => setField(`description_${lang}`, html)}
  format="html"
  renderInput={({ value, onChange, id, labelId, describedBy }) => (
    <RichTextEditor
      value={value}
      onChange={onChange}
      onUploadImage={uploadRichImage}
      id={id}
      labelledBy={labelId}
      describedBy={describedBy}
    />
  )}
/>
```

**Floating-Controls von `TranslationFormProvider`** (Sprachumschalter +
„alle Felder übersetzen“) sitzen per Default `fixed bottom-6 right-6 z-40`.
Kollidiert das mit einer eigenen Sticky-Leiste (z. B. Speichern/Abbrechen am
unteren Rand auf schmalen Screens), setzt das Tool die Position per
`controlsClassName` statt per CSS-Override auf die Utility-Klassen:

```tsx
<TranslationFormProvider translate={…} controlsClassName="fixed bottom-6 right-6 z-40 max-md:bottom-[5.5rem]">
```

**Verschieben:** Die schwebende Leiste hat links einen Griff (Ziehen mit
Maus/Touch, Pfeiltasten 16 px bzw. mit Umschalt 64 px; `Pos1`/`Esc` oder
Doppelklick setzen zurück). Der Versatz liegt als CSS-`translate` über der
Position aus `controlsClassName` und wird pro Browser in `localStorage`
(`basicbar_translation_controls_offset`) gemerkt. Abschalten mit
`movable={false}`.

**Andocken im Formular:** Wo die Leiste Inhalte verdecken würde (v. a. auf
Smartphones), setzt die Seite einen Platzhalter in den Fluss. Solange er
gemountet ist und `media` passt (Default `"(max-width: 767px)"`), rendert der
Provider die Leiste dort hinein – ohne Fixed-Positionierung und Griff; sonst
schwebt sie wie gewohnt. Bei mehreren Slots gewinnt der zuletzt gemountete –
auch wenn dessen `media` gerade nicht passt und ein älterer Slot passen würde
(dann schwebt die Leiste).

```tsx
<TranslationFormProvider
  translate={…}
  controlsClassName="fixed bottom-6 right-6 z-40"
  slotControlsClassName="flex justify-end" // Default: rechtsbündig
>
  …
  <form className="grid gap-6">
    <TranslationControlsSlot />           {/* optional: className, media */}
    <TranslatableField … />
  </form>
</TranslationFormProvider>
```

## Übersetzungs-Keys

Alle Strings des Pakets laufen über `t()` mit Englisch als Key (siehe
`initI18n`); das Tool stellt die deutschen (und weiteren) Übersetzungen in
seinem Katalog bereit. Fehlende Keys fallen auf den englischen Text zurück.

- Rich-Text-Editor: `"Bold"`, `"Italic"`, `"Heading (large)"`,
  `"Heading (small)"`, `"Bulleted list"`, `"Numbered list"`, `"Link"`,
  `"Enter URL"`, `"Insert image (or drag and drop)"`,
  `"Image upload failed"`, `"Image description (alt text)"`,
  `"Image description"`.
- TranslatableField: `"translated"`, `"not translated"`,
  `"translation may be outdated"`,
  `"The other language was changed since this translation."`,
  `"Mark as up to date"`, `"Translate from {{language}}"`,
  `"Translating…"`, `"Translation failed."`,
  `"A value in {{language}} is required."`.
- TranslationFormProvider: `"Show all fields in one language"`,
  `"Show all fields in {{language}}"`, `"Translate all fields"`,
  `"Translating…"`, `"Some fields could not be translated."`,
  `"Move translation controls"`.
- Preferences: `"Preferences"`, `"Language"`, `"Appearance"`, `"Auto"`,
  `"(follows your system)"`, `"Light"`, `"Dark"`.

## Preferences (language & appearance)

Three shared components, styled like the rest of the -bar menus:

- `LanguageOptions` (`{ onChange?, onPicked?, heading? }`) — a labelled
  `role="group"` with its "Language" heading (`heading={false}` hides it) and
  `menuitemradio` rows from `SUPPORTED_LANGUAGES`.
- `AppearanceControl` — a labelled `role="group"` with its "Appearance"
  heading and Auto / Light / Dark as `menuitemradio` rows (needs
  `ThemeProvider`). Both are valid inside a `role="menu"`.
- `PreferencesMenu` (`{ onLanguageChange? }`) — round button with a popover
  holding both (groups separated by a `role="separator"`); for signed-out visitors.

```tsx
// Signed-in: rows inside the app's own account menu
<LanguageOptions onChange={(lang) => api.setLanguage(lang)} onPicked={close} />
<AppearanceControl />

// Guests
<PreferencesMenu />
```

Language rule: there is no "Auto" entry. Without a manual pick the detector
follows the system and the shown language is the marked one; a pick calls
`i18n.changeLanguage`, which the detector caches, so it is binding from then
on. Use `onChange` / `onLanguageChange` to persist the choice server-side.

Keyboard: `PreferencesMenu` follows the WAI-ARIA menu pattern — opening
focuses the first row, Up/Down cycle through the rows, Home/End jump,
Escape closes and returns focus to the button. Translation keys: see
"Übersetzungs-Keys" above.

## CSP

Die Komponenten injizieren zur Laufzeit **keine** Inline-Styles oder
-Skripte, damit Tools eine strikte Content-Security-Policy
(`script-src 'self'; style-src 'self'`, ohne `'unsafe-inline'`) fahren können.
`RichTextEditor` läuft deshalb mit TipTaps `injectCSS: false`; die
ProseMirror-Grundregeln (Umbruchverhalten, Gapcursor, Auswahl) kommen aus
`base.css` — ein Tool, das `base.css` wie oben importiert, muss nichts weiter
tun. React-`style={{}}`-Props (CSSOM) sind unter `style-src 'self'` erlaubt.

Ausnahme: `prePaintScript()` liefert das Theme-Skript als String für ein
Inline-`<script>` in `index.html`. Unter einer strikten CSP schreibt das Tool
den Inhalt stattdessen in eine eigene Datei (z. B. `public/theme-init.js`) und
bindet sie synchron im `<head>` ein (so macht es ausleihbar, #44).
