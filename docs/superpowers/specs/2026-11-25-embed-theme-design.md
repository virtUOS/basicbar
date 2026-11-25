# `@basicbar/embed-theme`: anpassbares Erscheinungsbild für öffentliche Seiten — Design

Stand 2026-11-25. Neues Paket neben `@basicbar/ui`.

## Anlass und Warum

Kommunikation & Marketing der Universität Osnabrück bittet darum, dass Integrationen auf Uni-Seiten dem Uni-Layout folgen, also Farben, Schrift und Formen des Bootstrap-Styleguides der Website. Betroffen sind zuerst die eingebetteten bzw. öffentlichen Seiten zweier Tools:

- orientierBAR: Embed `/embed` und die Erklärungsseiten;
- ticketBAR: alle öffentlichen Seiten (`/embed`, `/e/…`, `/r/…`, die Erklärungsseiten).

Der Auftraggeber möchte zweierlei (2026-11-25):

- **Flexibilität für andere Betreiber:** Wer die Tools außerhalb der Uni Osnabrück betreibt, soll Farben, Schrift und Rundungen einfach anpassen können, ohne neu zu bauen. Gewählt ist eine Theme-Datei, die zur Laufzeit ausgeliefert und per Volume ersetzt wird.
- **Der Mechanismus kommt nach basicbar,** weil zwei Tools ihn brauchen.

## Ziele

- Ein Tool bindet das Paket ein und hat auf seinen öffentlichen Seiten:
  - die Uni-Osnabrück-Voreinstellung;
  - typgeprüfte CSS-Variablen, die eine Theme-Datei überschreiben kann;
  - Tailwind-Farben, die auf diese Variablen zeigen;
  - selbst ausgelieferte Signika;
  - ein Prüfskript für Kontraste.
- Ein Betreiber passt das Aussehen an, indem er eine Datei per Volume ablegt; ein Neubau ist nicht nötig.
- Das Paket funktioniert mit dem Stack von orientierBAR (React 19, Tailwind 4, Vite 8) und von ticketBAR (React 18, Tailwind 3, Vite 6), ohne dass ticketBAR vorher den Stack wechseln muss.

## Nicht-Ziele

- Keine Komponenten und kein React. Wie Knöpfe, Kacheln und Karten aussehen, bleibt Tool-Code; das Paket liefert nur Tokens und Hilfsmittel.
- Keine Pflegeoberflächen: `@basicbar/ui` mit `createPreset` und `base.css` bleibt unverändert.
- Kein Dunkelmodus: Öffentliche bzw. eingebettete Seiten sind hell.
- Kein Wechsel des Themes ohne Neuladen.

## Anti-Ziele

- Eine fehlende, kaputte oder teils ungültige Theme-Datei macht eine Seite unbenutzbar.
- Die Uni-Voreinstellung verfehlt WCAG-AA, weil Werte aus dem Uni-CSS ungeprüft übernommen werden.
- Das Paket oder eine Theme-Datei verursacht einen Abruf bei einem Dritten.
- Das Paket zwingt ein Tool in eine bestimmte Tailwind- oder React-Version.

## Randbedingungen

- **Rule of Two** (`CLAUDE.md`): In die Basis wandert, was zwei Tools brauchen und eines erprobt hat. Bedarf: orientierBAR und ticketBAR. Erprobung siehe „Ablauf“: Das Paket wird vor dem Release in orientierBAR eingebunden.
- **Distribution** (ADR-0002):
  - npm-Tarball als GitHub-Release-Asset, Tag `embed-theme/vX.Y.Z`, Publish-Job analog `ui/v*` (Draft, dann von Hand veröffentlichen).
  - Neuer CI-Job `embed-theme`. Das Ruleset „main“ muss ihn als Pflicht-Check aufnehmen (Settings → Rules, im selben Zug wie der Merge).
- **Browser** der Tools: Chrome/Edge ab 111, Firefox ab 128, Safari ab 16.4. `color-mix()` und `@property` werden in allen unterstützt. Die relative Farbsyntax (`oklch(from …)`) fehlt in Chrome bis 118 und wird nicht verwendet.
- **Signika** steht unter der SIL Open Font License 1.1 und darf mitgeliefert werden; die Lizenzdatei liegt bei.
- **Uni-Werte** (ausgelesen 2026-11-25 aus dem Bootstrap-Theme des Styleguides und dem CSS der Live-Site):
  - Primär #ad1034 (7,24:1 auf Weiß), Hover #8a0d2a, Text #3e3e3f, Fläche #f3f3f3;
  - Akzent #fbb800, nur als Balken (mit Weiß 1,76:1);
  - Signika, Fließtext Gewicht 300, alle Ecken 0.
  - Abweichungen wegen Barrierefreiheit:
    - Feldrahmen #767676 statt #ced4da (1,49:1);
    - Fehler #c8102e statt #dc1442 (auf #f3f3f3 nur 4,48:1);
    - Nebentext #5e5e5e.

## Betrachtete Wege

| Weg | Abwägung |
|---|---|
| **Eigenes Paket `@basicbar/embed-theme`** (gewählt, Auftraggeber 2026-11-25) | Kein React, keine Tailwind-Version vorgeschrieben, sofort in beiden Tools nutzbar. Ein Paket mehr mit eigenem Tag, CI-Job und Publish-Job. |
| Teil von `@basicbar/ui` | Kein neues Paket, aber ticketBAR (`ui` 0.7.0, React 18, Tailwind 3) müsste erst den Stack-Sprung machen. |
| Je Tool getrennt | Ursprünglich gewählt, dann verworfen: doppelte Arbeit samt Kontrastprüfung. |

## Design

### Inhalt des Pakets (`packages/embed-theme`)

- **`theme.css`**: vom Tool in seinen öffentlichen Einstiegen importiert.
  - `@property`-Registrierung jeder Farbvariable (`syntax: "<color>"`, `inherits: true`, `initial-value` = Uni-Wert). Ein ungültiger Wert fällt damit auf die Voreinstellung zurück.
  - Die Uni-Voreinstellung aller Variablen in `:root`, innerhalb `@layer basicbar-theme`. Die Theme-Datei des Betreibers ist ungeschichtet und gewinnt deshalb unabhängig von der Ladereihenfolge.
  - `@font-face` für Signika (variabel, Gewicht 300–700, nur lateinische Teilmenge) mit der mitgelieferten woff2-Datei. `font-display: swap`.
  - Abgeleitete Töne als weitere Variablen mit `color-mix()`, nicht konfigurierbar: getönter Hintergrund gewählter Elemente (etwa 8 % Primär auf Weiß), Hover-Fläche.
- **Variablen** (Präfix `--theme-`):

  | Variable | Uni-Voreinstellung |
  |---|---|
  | `--theme-primary` | #ad1034 |
  | `--theme-primary-hover` | #8a0d2a |
  | `--theme-on-primary` | #ffffff |
  | `--theme-accent` | #fbb800 |
  | `--theme-text` | #3e3e3f |
  | `--theme-muted` | #5e5e5e |
  | `--theme-surface` | #f3f3f3 |
  | `--theme-border` | #d0d0d0 (dekorativ) |
  | `--theme-field-border` | #767676 |
  | `--theme-danger` | #c8102e |
  | `--theme-radius` | 0 |
  | `--theme-font` | "Signika Variable", system-ui, sans-serif |
  | `--theme-font-weight` | 300 |
- **`tailwind.js`**: exportiert `themeColors` (und `themeFontFamily`, `themeBorderRadius`), Tailwind-Farbwerte, die auf die Variablen zeigen. Deckkraft-Modifikatoren (`bg-theme-primary/10`) müssen in Tailwind 3 (Funktion bzw. `<alpha-value>`) und Tailwind 4 funktionieren. Die Werte werden für beide Versionen gleich gebaut, etwa `color-mix(in srgb, var(--theme-primary) calc(<alpha-value> * 100%), transparent)`; das genaue Muster entscheidet der Builder nach einem Test in beiden Versionen. Die Tools hängen diese Farben unter einem eigenen Namen (z. B. `theme`) in die Konfiguration ihrer öffentlichen Seiten. Die Rampen `brand` und `slate` der Pflegeoberfläche bleiben unberührt.
- **`template/theme.css`**: kommentierte Vorlage für Betreiber. Jede Variable steht dort mit Uni-Wert, Bedeutung und Kontrastregel. Ein Tool kopiert sie in sein `public/theme/`, damit `/theme/theme.css` im Image existiert.
- **`bin/check-theme.mjs`**: Kommando `basicbar-check-theme [datei]`, Node ohne Abhängigkeiten.
  - Liest `--theme-`-Variablen mit Hex-Werten aus einer Theme-Datei, ergänzt fehlende durch die Voreinstellung und prüft diese Paare:
    - Text, Nebentext, Primär, Primär-Hover und Fehler auf Weiß und auf Fläche: ≥ 4,5:1;
    - On-Primary auf Primär und auf Primär-Hover: ≥ 4,5:1;
    - Primär auf dem getönten Hintergrund: ≥ 4,5:1;
    - Feldrahmen und Primär (Fokus) auf Weiß: ≥ 3:1.
  - Meldet jedes Paar unter der Schwelle mit Wert und Soll und endet dann mit Code 1. Nicht lesbare Werte (keine Hex-Farbe) ergeben eine Warnung.
  - Ohne Datei prüft es die Voreinstellung.
  - Die Logik liegt in einem Modul mit Tests; das Kommando ist eine dünne Hülle.
- **`README.md`**:
  - Für Tools: Einbindung, Tailwind 3/4, Caddy-Baustein, `<link>` in den HTML-Einstiegen, Prüfung in der Tool-CI.
  - Für Betreiber (Sie-Form): Variablen, Beispiel mit eigener Farbe und Schrift, Volume, Prüfskript; keine externen Schrift-Adressen (Datenschutz).
- **Lizenz:** Apache-2.0 für den Paketcode, OFL-1.1 für die Schriftdatei (`fonts/OFL.txt`), SPDX-Header wie üblich.
- **Abhängigkeiten:** keine zur Laufzeit; Tailwind ist keine Peer-Abhängigkeit.

### Vertrag mit den Tools (im README, nicht im Paket-Code)

- Die öffentlichen HTML-Einstiege laden `/theme/theme.css` per `<link>`.
- Caddy liefert `/theme/*` zuerst aus `/srv/theme`, einem optionalen Volume am Caddy-Dienst, sonst aus dem gebauten `/srv/www/theme`. Fehlt eine Datei, gibt es ein echtes 404 und keinen SPA-Rückfall. Kurze Cache-Dauer mit Revalidierung.
- Die Komponenten der öffentlichen Seiten verwenden nur die `theme`-Farben, `--theme-radius` und `--theme-font`, keine festen Farbwerte.
- Die Tool-CI ruft `basicbar-check-theme` für die mitgelieferte Vorlage auf.

### Ablauf

1. **Paket bauen** auf dem basicbar-Branch `feat/embed-theme`:
   - CI-Job `embed-theme` (Tests des Prüfskripts, `npm pack`, Prüfung der SPDX-Header);
   - Publish-Workflow für `embed-theme/v*`;
   - Dependabot-Eintrag;
   - CHANGELOG mit Einbindungsschritten.
2. **Erprobung in orientierBAR vor dem PR:** Das gepackte Tarball wird lokal in orientierBAR eingebunden (Design `orientierbar/docs/superpowers/specs/2026-11-25-orientierbar-embed-theme-design.md`), Tests und Ansicht werden geprüft. Erst dann geht der PR auf GitHub, nach ausdrücklicher Freigabe durch den Auftraggeber.
3. **Release:** Merge durch den Auftraggeber, Ruleset um `embed-theme` ergänzen, Tag `embed-theme/v0.1.0`, Release veröffentlichen.
4. **Konsumenten:** orientierBAR stellt auf die Release-URL um. ticketBAR folgt als eigenes Vorhaben.

## Tests

- **Prüfskript:**
  - Hex-Parser (#rgb, #rrggbb, Groß- und Kleinschreibung).
  - Kontrastformel gegen bekannte Werte, z. B. #ad1034 auf Weiß = 7,24.
  - Paarliste, fehlende Variablen fallen auf die Voreinstellung.
  - Nicht lesbare Werte geben eine Warnung, zu schwache Paare den Exit-Code 1.
  - Die Voreinstellung besteht.
- **Tailwind:** Ein kleiner Build-Test je Version (3 und 4) erzeugt `bg-theme-primary/10` und prüft, dass das erzeugte CSS gültig ist und die Variable verwendet.
- **CSS:** Ein Test prüft, dass jede Variable der Tabelle in `theme.css` registriert und mit Voreinstellung belegt ist und in `template/theme.css` dokumentiert ist.
- Ob eine Theme-Datei die Voreinstellung im Browser überschreibt, ungültige Werte zurückfallen und ein 404 nicht stört, prüfen die Tools mit Playwright, weil basicbar keinen Browser-Test hat.

## Dem Builder überlassen

- Das genaue Tailwind-Muster für Deckkraft in beiden Versionen.
- Woher die Signika-woff2 kommt (aus `@fontsource-variable/signika` beim Paketbau kopiert oder eingecheckt) und wie das Paket gebaut wird (reine Dateien, kein Bundler nötig).
- Wortlaut von README und Vorlage.
