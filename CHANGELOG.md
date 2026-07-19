# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/), ein Abschnitt
pro Paket-Release (Tag `<paket>/vX.Y.Z`). Jeder Eintrag nennt, was sich ändert
und was ein konsumierendes Tool beim Upgrade tun muss („Migration“) — dieses
Changelog ist die Upgrade-Anleitung für die Tools.

## [Unreleased]

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
