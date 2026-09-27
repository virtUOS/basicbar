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

## Rich text

`RichTextEditor` (TipTap) + `RichText` — der eine WYSIWYG-Editor für
formatierte Langtext-Felder (Fett, Kursiv, Aufzählungen, nummerierte Listen,
Link, Überschriften H2/H3, optional Bilder) und die passende Renderkomponente
für das gespeicherte HTML. Aus AbstimmBAR in die Basis verschoben
(modulierbar#5), damit alle -bar-Tools eine Implementierung teilen.

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
import { RichTextEditor } from "@basicbar/ui";

<RichTextEditor
  value={description}
  onChange={setDescription}
  ariaLabel={t("Description")}
/>
```

**Editor mit Bildern** — `onUploadImage` lädt hoch und liefert die relative
URL als String; scheitert der Upload, zeigt der Editor
`t("Image upload failed")` (plus die Fehlermeldung, falls vorhanden) per
`window.alert` und lässt den Inhalt unverändert:

```tsx
<RichTextEditor
  value={description}
  onChange={setDescription}
  onUploadImage={async (file) => {
    const response = await api.uploadRichImage(file);
    return response.url; // relative URL-String, z. B. "/media/rich/x.png"
  }}
  id="description-editor"
  ariaLabel={t("Description")}
/>
```

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
import { RichText } from "@basicbar/ui";

<RichText html={product.description} />
// eigene Klassen statt des Prosa-Defaults (ersetzt, nicht ergänzt):
<RichText html={product.description} className="text-3xl [&_img]:max-h-64" />
```

**Integration in `TranslatableField`** über `renderInput` (pro Sprache ein
Editor, mit `format="html"` bleiben die Ausgefüllt-Punkte markup-blind und
die Maschinenübersetzung erhält die Tags). `renderInput` bekommt neben `id`
auch `labelId` — die Id von `TranslatableField`s eigenem sichtbaren `<label>`
(nur gesetzt, wenn die `label`-Prop übergeben wurde); durchgereicht als
`labelledBy` bindet der Editor sich per `aria-labelledby` an dieses Label,
statt ein zweites, redundantes `ariaLabel` zu brauchen:

```tsx
<TranslatableField
  label={t("Description")}
  values={{ de: form.description_de, en: form.description_en }}
  onChange={(lang, html) => setField(`description_${lang}`, html)}
  format="html"
  renderInput={({ value, onChange, id, labelId }) => (
    <RichTextEditor
      value={value}
      onChange={onChange}
      onUploadImage={uploadRichImage}
      id={id}
      labelledBy={labelId}
    />
  )}
/>
```

**Übersetzungs-Keys**, die das Tool bereitstellen muss (Englisch als Key,
siehe `initI18n`): `"Bold"`, `"Italic"`, `"Heading (large)"`,
`"Heading (small)"`, `"Bulleted list"`, `"Numbered list"`, `"Link"`,
`"Enter URL"`, `"Insert image (or drag and drop)"`,
`"Image upload failed"`.
