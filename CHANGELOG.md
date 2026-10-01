# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/), ein Abschnitt
pro Paket-Release (Tag `<paket>/vX.Y.Z`). Jeder Eintrag nennt, was sich ändert
und was ein konsumierendes Tool beim Upgrade tun muss („Migration“) — dieses
Changelog ist die Upgrade-Anleitung für die Tools.

## [Unreleased]

### @basicbar/ui (→ wird `ui/v0.6.0`)

**Geteilte Einstellungs-Bausteine** (ausleihbar#35): `LanguageOptions`,
`AppearanceControl` und `PreferencesMenu`. Die ersten beiden sind Menüzeilen
für das Account-Menü des Tools (je eine beschriftete `role="group"` mit
`menuitemradio`-Zeilen, gültig in `role="menu"`; `LanguageOptions` hat
`heading?`); `PreferencesMenu` ist der runde Einstellungen-Button mit
Popover für nicht angemeldete Besucher. Es gibt bewusst keinen Eintrag „Auto“
bei der Sprache: ohne Wahl folgt der Detector dem System (die angezeigte
Sprache ist markiert), eine Wahl wird von i18next gecacht und ist damit
verbindlich. `onChange` / `onLanguageChange` dienen zum serverseitigen
Speichern. README: neuer Abschnitt „Preferences (language & appearance)“.

Migration: additiv, nichts zu tun. Die Tools ergänzen in ihren Katalogen den
Schlüssel „Preferences“ (die übrigen — Appearance, Auto, „(follows your
system)“, Light, Dark, Language — existieren meist schon).

### @basicbar/ui (→ wird `ui/v0.5.1`)

**CSP-tauglicher `RichTextEditor`** (basicbar#9): TipTap hängte beim Mounten
ein `<style data-tiptap-style>` mit den ProseMirror-Grundregeln an `<head>` —
unter einer Content-Security-Policy mit `style-src 'self'` (ohne
`'unsafe-inline'`) blockiert der Browser das, der Editor verliert dann u. a.
sein Umbruchverhalten. Der Editor läuft jetzt mit `injectCSS: false`; die
Regeln (unverändert aus `@tiptap/core` `src/style.ts`, TipTap 3.31) stehen in
`base.css` — bewusst außerhalb jedes `@layer`, weil Tailwind die zur Laufzeit
gesetzten `ProseMirror-*`-Klassen nicht sieht und gelayerte Regeln sonst
entfernen würde. README: neuer Abschnitt „CSP“.

Migration: keine, solange das Tool `@basicbar/ui/base.css` importiert (wie
im README beschrieben). Wer `base.css` nicht einbindet, muss die
ProseMirror-Regeln selbst bereitstellen.

### basicbar-integrations (→ wird `integrations/v0.2.1`)

**Sicherheitsfix:** `clean_media_url` prüfte den rohen String, sodass
Pfade wie `/media/%2e%2e/api/whoami/` oder `/media/a\..\b` durchkamen —
Browser lösen die enthaltenen `..`-Segmente nach dem Decodieren aber
trotzdem auf, sodass ein admin-verfasstes `<img>` einen same-origin GET
auf beliebige Pfade auslösen konnte (basicbar#6). Geprüft wird jetzt der
decodierte, normalisierte Pfad; einfach- und doppelt-encodierte
`..`-Segmente sowie Backslashes werden abgelehnt.

**Fix Runde 2 (basicbar#6):** drei weitere Bypasses, die der WHATWG-URL-
Parser aber ein reiner Substring-Check nicht sieht, sind jetzt ebenfalls
abgedeckt: rohe oder `%09`/`%0a`/`%0d`-codierte C0-/DEL-Steuerzeichen
(Browser entfernen sie überall im URL vor dem Auflösen, sodass z. B.
`/media/.&#9;./api/` sonst als `/api/` aufgelöst würde); ein `?`/`#`
(roh oder codiert), das ein `..` davor verbirgt (`/media/..?x` →
`/?x`); und `url[:300]`-Truncation *nach* der Validierung, die einen
validierten langen Pfad nachträglich wieder auf eine Traversal kürzen
konnte — über 300 Zeichen wird jetzt komplett abgelehnt statt gekürzt.

Migration: keine — reiner Bugfix, die öffentliche Signatur von
`clean_media_url`/`clean_html` ändert sich nicht.

### @basicbar/ui (→ wird `ui/v0.5.0`)

**Alt-Text für Bilder in `RichTextEditor`** (basicbar#7, WCAG 1.1.1): direkt
nach einem erfolgreichen Bild-Upload fragt der Editor per `window.prompt`
nach einer Beschreibung (`t("Image description (alt text)")`) — leere
Eingabe oder Abbrechen setzen beide `alt=""` (bewusst dekoratives Bild), das
Bild wird in jedem Fall eingefügt. Neuer Toolbar-Button
`t("Image description")` (nur sichtbar, wenn `onUploadImage` gesetzt ist),
deaktiviert, solange kein Bild markiert ist; bei markiertem Bild öffnet er
denselben Prompt vorausgefüllt mit dem aktuellen Alt-Text und übernimmt
Änderungen per `updateAttributes("image", { alt })` — Abbrechen lässt den
bestehenden Alt-Text unangetastet. `ToolbarButton` hat dafür eine neue
optionale `disabled`-Prop (reduzierte Deckkraft, `aria-disabled`).

Nebenbei behoben: `useEditor` setzt jetzt `shouldRerenderOnTransaction: true`
— TipTap 3 rendert standardmäßig nicht mehr bei reinen Selektionsänderungen
neu, sodass sämtliche Toolbar-Buttons (Fett/Kursiv/Überschriften/Link und
jetzt auch der neue Bildbeschreibungs-Button), die ihren aktiven/deaktivierten
Zustand aus `editor.isActive(...)` lesen, nach einem Klick ohne Dokument-
änderung (z. B. Bild ab-/anwählen) den alten Stand zeigten, bis die nächste
Bearbeitung ein Re-Render auslöste.

Migration: keine für Tools ohne `onUploadImage` — additiv. Tools mit
Bild-Upload ergänzen die neuen Übersetzungs-Keys
`"Image description (alt text)"` und `"Image description"`.

### @basicbar/ui (→ wird `ui/v0.4.0`)

**`RichTextEditor` + `RichText`** (modulierbar#5), aus AbstimmBAR verschoben:
der eine WYSIWYG-Editor (TipTap) für formatierte Langtext-Felder — Fett,
Kursiv, Aufzählungen, nummerierte Listen, Link, Überschriften (H2/H3) und
optional Bilder — plus `RichText` zum Rendern des gespeicherten HTML.
Bilder (Toolbar-Button, Drag&Drop, Einfügen aus der Zwischenablage) gibt es
nur, wenn die App `onUploadImage(file) => Promise<string>` übergibt (relative
URL, z. B. `/media/rich/x.png`); ohne die Prop bleiben bestehende `<img>`-
Inhalte sichtbar, es lassen sich nur keine neuen einfügen. Auf
Upload-Fehler zeigt der Editor `t("Image upload failed")` per
`window.alert` und lässt den Inhalt unverändert. Passt zum
Sanitizing-Vertrag von `basicbar_integrations.html_sanitize.clean_html`
(oder einem gleichwertigen Allowlist-Sanitizer im Tool) — die gespeicherte
HTML wird dort auf genau dieses Subset reduziert. Eingefügtes Rich-HTML
(z. B. aus einer Webseite kopiert) wird per `transformPastedHTML` gefiltert:
jedes `<img>`, dessen `src` nicht mit `/media/` beginnt, wird entfernt —
ohne `onUploadImage` wird jedes eingefügte `<img>` entfernt. So kann kein
externes Bild am Upload-Flow vorbei ins Dokument gelangen; vorhandene Bilder
im initialen `value` bleiben unangetastet.

Neue Dependencies: `@tiptap/react`, `@tiptap/pm`, `@tiptap/starter-kit`,
`@tiptap/extension-link`, `@tiptap/extension-image`,
`@tiptap/extension-bold` (alle `^3.27.2`); `react-dom` (`>=18`) ist jetzt
zusätzlich zu `react` als Peer-Dependency deklariert (`@tiptap/react`
importiert es zur Laufzeit).

Der Editor bietet bewusst nur das Subset an, das der Sanitizer behält:
Unterstreichen/Durchgestrichen sind nicht registriert und Links tragen kein
`target`/`rel` (das Backend erzwingt `rel="noopener"` ohnehin). Der externe
`value`-Sync (Sprachwechsel u. ä.) läuft jetzt außerhalb der Undo-History
(`setMeta("addToHistory", false)`), damit ein Undo direkt danach nicht in
den vorherigen Inhalt hineinspringt. `RichTextEditor` hat eine neue optionale
Prop `labelledBy` (Id eines externen `<label>`, Alternative zu `ariaLabel`);
`RenderInputArgs` (für `renderInput`) hat entsprechend ein neues optionales
Feld `labelId` — `TranslatableField`s eigene Label-Id, additiv und
abwärtskompatibel. Der Bild-Upload-Button ist jetzt per `aria-label` benannt
und zeigt einen sichtbaren Fokusring; ein fehlgeschlagener Bild-Upload zeigt
zusätzlich zu `t("Image upload failed")` die Fehlermeldung, falls vorhanden.

Migration: keine für Tools, die die Komponente noch nicht nutzen — additiv.
Ein Tool, das den Editor einsetzt, übernimmt `RichTextEditor`/`RichText`
aus `@basicbar/ui` statt einer lokalen Kopie (z. B. via
`TranslatableField`s `renderInput`, `labelledBy={labelId}` durchreichen) und
ergänzt die Übersetzungs-Keys `"Bold"`, `"Italic"`, `"Heading (large)"`,
`"Heading (small)"`, `"Bulleted list"`, `"Numbered list"`, `"Link"`,
`"Enter URL"`, `"Insert image (or drag and drop)"`, `"Image upload failed"`.

### @basicbar/ui (→ wird `ui/v0.3.1`)

**Globaler Sprach-Umschalter** (modulierbar#99): Der schwebende
Übersetzungs-Block zeigt jetzt einen kompakten DE/EN-Umschalter, der mit
einem Klick **alle** gemounteten `TranslatableField` auf eine Sprache stellt
(über den bestehenden `forced`-Mechanismus, ohne zu übersetzen) — praktisch,
um einen Datensatz Feld für Feld in einer Sprache zu befüllen. Sichtbar,
sobald mehrsprachige Felder auf dem Bildschirm sind (unabhängig von der
Maschinenübersetzung); der „Alle Felder übersetzen"-Button bleibt daran
gekoppelt.

Migration: keine — rein additiv. Neue UI-Strings `"Show all fields in one
language"` und `"Show all fields in {{language}}"` (Tools ergänzen ihre
Übersetzungen).

### basicbar-integrations (→ wird `integrations/v0.2.0`) und @basicbar/ui (→ wird `ui/v0.3.0`)

**Veraltete Übersetzungen markieren** (modulierbar#31, generisch für alle
Tools): Wird eine Sprache nach der Übersetzung geändert, gilt die
unveränderte Gegensprache als „möglicherweise veraltet“ — sichtbar im
Editor, abfragbar im Release-Prozess, per „Als aktuell markieren“
quittierbar. Ändern sich beide Sprachen, wird nichts markiert (bewusste
Doppel-Korrektur). Felder ohne aufgezeichneten Sync-Stand (Bestandsdaten)
werden nie markiert.

- `basicbar_integrations.translation_sync` (neu): `content_hash`,
  `record_synced`, `changed_languages`, `stale_languages`, `stale_map`,
  `modeltranslation_values`. Zustand lebt pro Model in einem vom Tool
  angelegten `JSONField` (eine Zeile + Migration).
- `@basicbar/ui` `TranslatableField`: neue optionale Props `stale`
  (Sprachcodes → amber Tab-Punkt + Hinweiszeile), `onMarkSynced`
  („Als aktuell markieren“) und `onTranslated` (nach Maschinen-
  übersetzung — hier den Sync-Stand persistieren). Der Übersetzen-Button
  erscheint bei veralteten Sprachen auch auf gefülltem Feld (explizites
  Neu-Übersetzen); `TranslationForm`-Einträge unterstützen `onTranslated`
  ebenfalls („alle Felder übersetzen“ hält den Sync-Stand aktuell,
  überschreibt aber weiterhin nie gefüllte Felder).

Migration (Adoption ist opt-in — ohne neue Props/Aufrufe ändert sich nichts):
1. Model: `translation_sync = models.JSONField(default=dict, blank=True)`
   + Migration.
2. Beim Speichern übersetzungsrelevanter Endpunkte bzw. in einem eigenen
   „mark synced“-/`onTranslated`-Endpunkt: `record_synced()` aufrufen.
3. Serializer: `translation_stale = stale_map(instance.translation_sync,
   {feld: modeltranslation_values(instance, feld, ("de", "en")), …})`
   ausliefern; Frontend reicht es als `stale`-Prop durch und ruft bei
   `onMarkSynced`/`onTranslated` den Endpunkt aus Schritt 2.
4. Release-Checks: `stale_map()` über die zu prüfenden Objekte.
5. Neue Katalog-Schlüssel (de-Übersetzungen ergänzen):
   `translation may be outdated`, `The other language was changed since
   this translation.`, `Mark as up to date`.

## lti/v0.1.2 — 2026-07-19

### basicbar-lti
- LTI-1.3-Fundament (Phase 5), aus abstimmbar extrahiert: `LtiPlatform`/
  `LtiToolKey`/`LtiUserLink`, `build_tool_conf`, `lti_login`/`lti_jwks`,
  Staff-Platform-API, JIT-Provisionierung mit E-Mail-Unifizierung
  (Opt-in pro Plattform), Constraint-Namen mit Paket-Präfix (koexistenz-
  sicher während der Umzugsmigration), Frame-Ancestors-Middleware
  (`LTI_FRAME_PATH_PREFIXES` konfigurierbar). 28 Tests inkl. simuliertem
  LMS-Handshake.
- Bewusst Tool-seitig: Message-Launch, Deep Linking, Kontext-Link-Model
  (FK auf Fachmodelle) und Icon — komponiert aus den Paket-Primitiven.
- Migration abstimmbar: Daten-Umzugsmigration (`lti/0003`) kopiert
  Plattformen/Keys/User-Links PK-erhaltend in die Paket-Tabellen und hängt
  den Kontext-Link-FK um — läuft als normales `manage.py migrate`, kein
  manueller Schritt.
- ausleihbar: keine Änderung — die Fähigkeit kommt bei Bedarf über
  Paket + eigene Launch-App.

## auth/v0.1.0 — 2026-07-19

### basicbar-auth
- Erstes Auth-Paket (Phase 4): `OIDCBackend` (Claim-Mapping, JIT-
  Provisionierung, IdP-Gruppen → Django-Admin), `SilentLoginView`,
  Back-Channel-Logout, `provider_logout_url`, `is_oidc_admin`,
  `discovery.discover_endpoints`, `AbstractBasicUser` (ADR-0003).
- Die bewussten Tool-Unterschiede aus Phase 0 sind jetzt Konfiguration:
  `MAX_USERS` (Obergrenze; `anonymized_at`-Konvention zählt anonymisierte
  Konten nicht) und `OIDC_MATCH_BY_USERNAME_FALLBACK` (Subject-Drift-
  Heilung per Username-Match, Default aus). Betreiber-Doku zu Fristen und
  Kennungs-Wiedervergabe im Paket-README.
- 25 Tests (aus beiden Tools portiert und vereinigt, inkl. der neuen
  Flag-Pfade), eigener CI-Job.
- Migration beide Tools: `accounts/oidc.py` + `config/oidc_discovery.py`
  löschen; `AUTHENTICATION_BACKENDS`/`OIDC_OP_LOGOUT_URL_METHOD` auf
  `basicbar_auth.oidc.*`; Importe in urls/views/serializers umstellen;
  `INSTALLED_APPS` + `basicbar_auth`. User-Model bleibt unangetastet.
- Migration abstimmbar zusätzlich: `OIDC_MATCH_BY_USERNAME_FALLBACK=True`
  setzen (bisheriges Verhalten, an der UOS unkritisch — Kennungen werden
  nicht neu vergeben).

## ui/v0.2.1 — 2026-07-19

### @basicbar/ui
- Neu: `TranslatableField` + `TranslationFormProvider`/`useTranslationForm` —
  die vereinheitlichte Übersetzungs-Editor-Komponente beider Tools.
  Vertrag: per Sprache (`values` + `onChange(lang, text)`), n Sprachen aus
  `SUPPORTED_LANGUAGES` (UI-Sprache-zuerst), `renderInput` für
  Custom-Editoren, `singleLanguage` (Easy Mode) als Prop, `format="html"`
  (Statuspunkte ignorieren Markup, Übersetzung erhält es),
  `MAX_TRANSLATE_LENGTH`-Kappe. Der HTTP-Aufruf wird vom Tool injiziert:
  `<TranslationFormProvider translate={…}>`.
- Neue Peer-Dependency: `lucide-react`.
- Migration beide Tools: lokale `TranslatableField`/`TranslationForm`
  ersetzen; `tailwind.config` `content` um
  `./node_modules/@basicbar/ui/dist/**/*.js` erweitern (Komponenten-Klassen
  müssen gescannt werden); Provider bekommt die `translate`-Funktion.
- Migration ausleihbar: `api.translate` um `format`-Parameter erweitern;
  Aufrufstellen bleiben unverändert (gleicher Feld-Vertrag).
- Migration abstimmbar: lokaler Wrapper behält `value`/`onChange(next)`,
  `variant="rich"` (RichTextEditor) und Easy Mode; Tab-Reihenfolge folgt
  jetzt der UI-Sprache statt fix kanonisch-zuerst.

## ui/v0.1.0 — 2026-07-19

### @basicbar/ui
- Erstes UI-Paket (Phase 3), Modell „ein Designsystem, pro Tool ein eigener
  Akzent“: `createPreset({ colors })` (Font, Dark Mode per `.dark`-Klasse,
  Motion-Tokens; die `slate`/`brand`-Ramps bleiben als Identität im Tool),
  `base.css` (A11y-Basis: focus-visible-Ring, Skip-Link, reduced-motion,
  color-scheme, accent-color), `ThemeProvider`/`useTheme`/`prePaintScript`
  (Auto/Light/Dark, `storageKey` konfigurierbar), `initI18n({ resources })`
  und `contentLang`.
- Distribution: npm-Tarball via GitLab Generic Package Registry,
  CI-Publish beim Tag `ui/vX.Y.Z`.
- Migration ausleihbar: tailwind.config auf Preset, index.css auf
  `@import "@basicbar/ui/base.css"`, theme.tsx/i18n.ts/contentLang.ts
  löschen und Importe auf `@basicbar/ui` umstellen.
- Migration abstimmbar: dito; zusätzlich ThemeProvider statt des lokalen
  Theme-Moduls (mit `storageKey="abstimmbar_theme"` für Bestandsnutzer).

## integrations/v0.1.0 — 2026-07-19

### basicbar-integrations
- Erstes Paket (Phase 2): `ai` (LiteLLM-Client) und `translation_service`
  (LibreTranslate-Client) aus den konsolidierten Tool-Fassungen übernommen;
  Settings-Zugriff jetzt mit Paket-Defaults (`conf.py`) — unkonfiguriert ist
  alles aus, ein Tool ohne Settings-Block startet unverändert.
- Kanonischer Translate-Endpunkt: `POST {text, source, target, format?}` →
  `{translated}`; Sprachvalidierung, HTML-Sanitizing (`html_sanitize.py` aus
  abstimmbar, jetzt mit nh3-Abhängigkeit), englische Fehlertexte.
- Neu: Capabilities-Endpoint (`GET` → `{"translation": bool, "ai": bool}`,
  erweiterbar per `extra_capabilities()`).
- Migration ausleihbar: Response-Key `translation` → `translated`, URL
  `/api/manage/translate/` → Paket-URL, `TranslateView`-Subclass für die
  `IsLenderOrAdmin`-Permission, Format-Validierung neu.
- Migration abstimmbar: Fehlertexte nun englisch; Imports `common.ai` /
  `common.translation_service` / `common.html_sanitize` →
  `basicbar_integrations.*`.

### Repo
- Phase 1: Repo-Gerüst, ADRs 0001–0003, CI (SPDX-Check), Extraktionsplan.
- CI: Testjob für basicbar-integrations (python:3.12-slim).
