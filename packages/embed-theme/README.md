# @basicbar/embed-theme

Einheitliches, konfigurierbares Erscheinungsbild für die **öffentlichen
Seiten** der virtUOS „-bar“-Tools, wenn sie in fremde Seiten (Moodle,
Hochschul-Website) eingebettet oder unter fremder Adresse betrieben werden.
Das Paket liefert Theme-Variablen mit Uni-Osnabrück-Voreinstellung, die
Schrift Signika, Tailwind-Werte und ein Prüfskript für den Kontrast. Wer ein
Tool betreibt, ändert Farben, Eckenradius und Schrift in **einer Datei**,
ohne neu zu bauen.

Keine Laufzeit-Abhängigkeiten. Tailwind ist keine Peer-Abhängigkeit.

## Inhalt

| Datei | Zweck |
|---|---|
| `theme.css` | `@property`-Registrierung, Voreinstellung in `@layer basicbar-theme`, `@font-face` für Signika |
| `tailwind.js` | `themeColorsV3`, `themeColorsV4`, `themeBorderRadius`, `themeFontFamily` |
| `template/theme.css` | kommentierte Vorlage für Betreiber |
| `bin/check-theme.mjs` | Kommando `basicbar-check-theme` (Kontrastprüfung) |
| `fonts/` | Signika (variabel, lateinisch), Lizenz `OFL.txt` |

Lizenz: Apache-2.0 für den Code, OFL-1.1 für die Schriftdatei.

## Variablen

| Variable | Voreinstellung | Bedeutung |
|---|---|---|
| `--theme-primary` | `#ad1034` | Hauptfarbe: Schaltflächen, Links, Fokus |
| `--theme-primary-hover` | `#8a0d2a` | Hauptfarbe beim Darüberfahren |
| `--theme-on-primary` | `#ffffff` | Schrift auf der Hauptfarbe |
| `--theme-accent` | `#fbb800` | Akzent, nur Fläche oder Zierde |
| `--theme-text` | `#3e3e3f` | Fließtext |
| `--theme-muted` | `#5e5e5e` | Nebentext |
| `--theme-surface` | `#f3f3f3` | heller Hintergrund |
| `--theme-border` | `#d0d0d0` | dekorative Linien |
| `--theme-field-border` | `#767676` | Rahmen von Eingabefeldern |
| `--theme-danger` | `#c8102e` | Fehler |
| `--theme-radius` | `0` | Eckenradius |
| `--theme-font` | `"Signika Variable", system-ui, sans-serif` | Schriftfamilie |
| `--theme-font-weight` | `300` | Standard-Schriftgewicht |

Dazu zwei abgeleitete, nicht konfigurierbare Töne in `theme.css`:
`--theme-primary-tint` (8 % Primärfarbe auf Weiß) und `--theme-hover-surface`
(4 %).

Kontrastschwellen (WCAG 2.2 AA), die `basicbar-check-theme` prüft:

- 4,5:1: `text`, `muted`, `primary`, `primary-hover`, `danger`, jeweils auf
  Weiß und auf `surface`; `on-primary` auf `primary` und auf
  `primary-hover`; `primary` auf `primary-tint`.
- 3:1: `field-border` auf Weiß. `primary` auf Weiß (Fokus) ist durch die
  4,5:1-Prüfung mit abgedeckt.

---

# Für Tools (Entwickler)

## Installation

Per Release-URL, wie `@basicbar/ui`. In der `package.json` des Frontends:

```json
"@basicbar/embed-theme": "https://github.com/virtUOS/basicbar/releases/download/embed-theme/v0.1.0/basicbar-embed-theme-0.1.0.tgz"
```

## theme.css einbinden

In den öffentlichen Einstiegen (nicht in der Pflegeoberfläche) importieren:

```css
@import "@basicbar/embed-theme/theme.css";
```

Zusätzlich laden die öffentlichen HTML-Einstiege die **Theme-Datei des
Betreibers** per `<link>`, nach dem gebauten Stylesheet:

```html
<link rel="stylesheet" href="/theme/theme.css">
```

Die Datei der Voreinstellung ist geschichtet (`@layer basicbar-theme`), die
Theme-Datei des Betreibers ungeschichtet: Sie gewinnt unabhängig von der
Ladereihenfolge. Kopieren Sie dazu die Vorlage in den Build, damit
`/theme/theme.css` im Image existiert und das Tool ohne Volume die
Voreinstellung zeigt:

```bash
mkdir -p public/theme
cp node_modules/@basicbar/embed-theme/template/theme.css public/theme/theme.css
```

Die Komponenten der öffentlichen Seiten verwenden nur die `theme`-Farben,
`--theme-radius` und `--theme-font`, keine festen Farbwerte.

## Tailwind 3

```js
// tailwind.config.js (nur die Konfiguration der öffentlichen Seiten)
import { themeColorsV3, themeBorderRadius, themeFontFamily } from "@basicbar/embed-theme/tailwind";

export default {
  theme: {
    extend: {
      colors: { theme: themeColorsV3 },
      borderRadius: themeBorderRadius,
      fontFamily: themeFontFamily,
    },
  },
};
```

Dann gelten `bg-theme-primary`, `text-theme-text`, `bg-theme-primary/10`,
`rounded-theme` und `font-theme`. Die Werte enthalten `<alpha-value>`, damit
Deckkraft-Modifikatoren in Tailwind 3 funktionieren. Die Rampen `brand` und
`slate` der Pflegeoberfläche bleiben unberührt.

## Tailwind 4

Im JS-Konfigurationsmodus mit `@config`, und die **V4-Werte** (schlichte
`var()`-Werte, Tailwind 4 bildet Deckkraft selbst mit `color-mix`):

```js
// theme.config.js
import { themeColorsV4, themeBorderRadius, themeFontFamily } from "@basicbar/embed-theme/tailwind";

export default {
  theme: {
    extend: {
      colors: { theme: themeColorsV4 },
      borderRadius: themeBorderRadius,
      fontFamily: themeFontFamily,
    },
  },
};
```

```css
/* index.css */
@import "tailwindcss";
@config "./theme.config.js";
```

Verwenden Sie je Tailwind-Version den passenden Export: `themeColorsV3`
unter Tailwind 4 würde die Deckkraft doppelt berechnen.

`rounded-theme` setzen Sie selbst an die Elemente, die der Betreiber
abrunden darf. Punkte, Avatare und `rounded-full` bleiben rund.

## Caddy

`/theme/*` kommt zuerst aus `/srv/theme`, einem optionalen Volume, sonst
aus dem gebauten `/srv/www/theme`. Fehlt die Datei, gibt es ein echtes 404
und keinen Rückfall auf die SPA-`index.html`. Die Cache-Dauer ist kurz, mit
Revalidierung, damit Änderungen des Betreibers zeitnah wirken. Der Block
steht **vor** dem `handle` der SPA:

```caddyfile
	handle_path /theme/* {
		header Cache-Control "public, max-age=300, must-revalidate"
		@volume file {
			root /srv/theme
			try_files {path}
		}
		handle @volume {
			root * /srv/theme
			file_server
		}
		handle {
			root * /srv/www/theme
			file_server
		}
	}
```

Am Caddy-Dienst in `docker-compose.prod.yml` das Volume ergänzen (ein
Host-Ordner oder ein benanntes Volume, nur lesend):

```yaml
    volumes:
      - ./theme:/srv/theme:ro
```

Ein leerer oder fehlender Host-Ordner ist unkritisch: dann greift
`/srv/www/theme`.

## Prüfung in der Tool-CI

```bash
npx basicbar-check-theme --strict node_modules/@basicbar/embed-theme/template/theme.css
```

Die Kurzform `npx basicbar-check-theme` setzt voraus, dass
`@basicbar/embed-theme` im Projekt installiert ist (`npm ci` vorher). **Rufen
Sie `npx basicbar-check-theme` nie ohne installiertes Paket auf:** `npx`
würde sonst ein unbeteiligtes Paket gleichen Namens aus der npm-Registry
suchen und ausführen.

Aufruf: `basicbar-check-theme [--strict] [datei]`. Ohne Datei prüft es die
Voreinstellung. Exit 0: in Ordnung. Exit 1: ein Paar liegt unter der
Schwelle (mit `--strict` auch: Wert nicht lesbar). Exit 2: Datei nicht
lesbar. Ohne `--strict` erzeugt ein Wert, der keine Hex-Farbe ist, nur eine
Warnung, und das Paar wird übersprungen.

Ob eine Theme-Datei die Voreinstellung im Browser überschreibt, ungültige
Werte zurückfallen und ein 404 nicht stört, prüfen die Tools mit einem
Browser-Test (Playwright); das Paket hat keinen.

---

# Für Betreiber

Sie passen Farben, Eckenradius und Schrift der öffentlichen Seiten an, ohne
das Tool neu zu bauen.

1. Nehmen Sie die Vorlage `template/theme.css` (im Paket oder unter
   `/theme/theme.css` im laufenden Tool) und legen Sie sie als `theme.css`
   in den Ordner, der als Volume unter `/srv/theme` am Caddy-Dienst
   eingebunden ist.
2. Entfernen Sie bei den Zeilen, die Sie ändern wollen, die
   Kommentarzeichen und tragen Sie Ihren Wert ein. Alle anderen Zeilen
   behalten die Voreinstellung.
3. Prüfen Sie die Datei (siehe unten) und laden Sie die Seite neu. Der
   Browser holt die Datei spätestens nach fünf Minuten neu.

**Nur einfache `:root`-Werte.** Die Datei darf weder `@media` noch einen
Dunkelmodus noch `@layer` enthalten. Das Prüfskript liest sie Zeile für
Zeile und wertet keine Blöcke aus; ein Wert innerhalb von `@media` würde den
Grundwert überschreiben, ohne dass die Prüfung es bemerkt. Ohne `@layer` gewinnt Ihre
Datei gegen die Voreinstellung, egal in welcher Reihenfolge geladen wird.

## Beispiel: eigene Farbe

```css
:root {
  --theme-primary: #00539f;
  --theme-primary-hover: #003d75;
  --theme-on-primary: #ffffff;
}
```

Ändern Sie `primary-hover` immer mit: Er soll dunkler sein als `primary` und
ebenfalls genug Kontrast zu Weiß und zu `on-primary` haben. Gültige Werte für
`--theme-radius` sind zum Beispiel `0`, `4px` oder `0.5rem`.

## Beispiel: eigene Schrift

Legen Sie die Schriftdatei (woff2) in dasselbe Volume, etwa
`/srv/theme/fonts/meine-schrift.woff2`, und binden Sie sie in der Theme-Datei
mit `@font-face` ein. `@font-face` ist erlaubt; es ist kein `@media` und kein
`@layer`.

```css
@font-face {
  font-family: "Meine Schrift";
  font-weight: 300 700;
  font-display: swap;
  src: url("/theme/fonts/meine-schrift.woff2") format("woff2");
}

:root {
  --theme-font: "Meine Schrift", system-ui, sans-serif;
}
```

Wenn Sie die Schrift ändern, behalten Sie am Ende der Liste die
Ausweichschriften bei.

## Prüfen

```bash
npx --yes --package=https://github.com/virtUOS/basicbar/releases/download/embed-theme/v0.1.0/basicbar-embed-theme-0.1.0.tgz basicbar-check-theme --strict theme.css
```

Die Version in der Adresse (hier 0.1.0) muss zu der des Tools passen; sie
steht in der `package.json` des Tools. Rufen Sie `npx basicbar-check-theme`
**nie** ohne diese `--package`-Angabe auf, wenn das Paket nicht installiert
ist: `npx` würde ein fremdes Paket gleichen Namens aus der npm-Registry
laden und ausführen.

Das Skript nennt jedes Farbpaar mit zu geringem Kontrast, mit Ist- und
Sollwert. Beheben Sie diese Meldungen, bevor Sie die Datei einsetzen. Der
Kontrast gehört zur Barrierefreiheit der Seite: Besucher mit
Sehbehinderung können sonst Texte oder Schaltflächen nicht lesen.

## Datenschutz

Verwenden Sie **keine externen Adressen** in der Theme-Datei: keine
Google-Fonts-URL, kein `@import` von einem fremden Server, keine Bilder von
Dritten. Jeder solche Aufruf übermittelt die IP-Adresse der Besucher an
den fremden Anbieter. Legen Sie Schriften und andere Dateien in das Volume
und verweisen Sie mit `/theme/…` darauf.
